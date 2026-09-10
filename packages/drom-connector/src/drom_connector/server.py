"""baza.drom.ru MCP connector.

baza.drom.ru is Russia's primary automotive marketplace and classifieds site:
auto parts (new, used, contractual), tires, wheels, oils, tuning, and general
bulletins.

Tier 2 fetches inside the operator's logged-in Chrome over CDP;
tier 1 is impersonated HTTPS when a residential RU proxy is configured.
baza.drom.ru uses charset=windows-1251 for its HTML and canonical query strings.

NEVER write to stdout in a stdio MCP server — it corrupts JSON-RPC. Use
``log_event`` (stderr) or the ``Context`` logging methods.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import re
import urllib.parse
from typing import Annotated, Any, Literal, cast

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi
from fastmcp import Context, FastMCP
from fastmcp.server.middleware.error_handling import RetryMiddleware
from mcp.types import ToolAnnotations
from mcp_core import resilience as R
from mcp_core.cache import TTLCache
from mcp_core.errors import (
    BadRequestError,
    NotFoundError,
    ToolError,
    TransportDownError,
    raise_tool_error,
)
from mcp_core.output_schema import apply_compact_output_schemas
from mcp_core.pacing import Pacer
from mcp_core.redact import redact_error_text as _redact
from mcp_core.transport.chrome_cdp import NavBlocked, open_page
from pydantic import Field

from drom_connector.models_output import (
    DromCardResponse,
    DromFeedbackOut,
    DromSearchItemOut,
    DromSearchResponse,
    DromSelfcheckResponse,
    DromSellerOut,
    DromSellerResponse,
    MetaOut,
)
from drom_connector.settings import get_settings
from drom_connector.shape_reference import CARD_REQUIRED_KEYS, SEARCH_REQUIRED_KEYS, missing_required_keys

_settings = get_settings()

SERVER_VERSION = "2.1.0"
SERVER_STARTED_AT = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

SITE_BASE = "https://baza.drom.ru"

TIMEOUT = _settings.timeout
MAX_BODY_BYTES = _settings.max_body_bytes
IMPERSONATE = _settings.impersonate
_min_gap = _settings.min_gap

DROM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": f"{SITE_BASE}/",
}

_ITEM_ID_RE = re.compile(r"(?:-|\bg)(\d{6,})(?:\.html|\?|/|$)")
_GOOD_ID_RE = re.compile(r"(?:-g|/g)(\d{6,})")

mcp = FastMCP(
    name="drom-connector",
    version=SERVER_VERSION,
    instructions=(
        "baza.drom.ru auto parts, tires, wheels, oils and classifieds: search, item cards and seller profiles. "
        "Read-only, no credentials. Tier 2 fetches inside the operator's Chrome over CDP; "
        "tier 1 is impersonated HTTPS when residential proxy is available. "
        "Start with drom_search; drom_card takes an item id or URL; "
        "drom_seller takes a seller profile URL or id."
    ),
)
mcp.add_middleware(RetryMiddleware())

_cache: TTLCache = TTLCache(ttl_s=_settings.cache_ttl, max_entries=256)
_pacer = Pacer(_min_gap)
_cdp_lock = asyncio.Lock()


def _proxy() -> str | None:
    return _settings.proxy.get_secret_value() or None


async def _polite_wait() -> None:
    """Space requests out politely."""
    await _pacer.wait(min_gap=_min_gap)


def _encode_cp1251_query(query: str) -> str:
    """Encode search query using cp1251 (baza.drom.ru canonical encoding)."""
    try:
        return urllib.parse.quote_plus(query.encode("cp1251"))
    except (UnicodeEncodeError, LookupError):
        return urllib.parse.quote_plus(query)


def _sync_curl_get(url: str, proxy: str | None = None) -> tuple[int, str]:
    """Tier-1: curl_cffi GET with body cap and cp1251 fallback decoding."""
    kwargs: dict[str, Any] = {}
    if proxy:
        kwargs["proxies"] = {"http": proxy, "https": proxy}
    chunks: list[bytes] = []
    total = 0
    r = cffi.get(url, headers=DROM_HEADERS, impersonate=cast(Any, IMPERSONATE), timeout=TIMEOUT, stream=True, **kwargs)
    try:
        encoding = r.encoding or "cp1251"
        for chunk in r.iter_content(chunk_size=64 * 1024):
            total += len(chunk)
            if total > MAX_BODY_BYTES:
                raise ValueError(f"body exceeds {MAX_BODY_BYTES} bytes")
            chunks.append(chunk)
        body = b"".join(chunks)
        try:
            text = body.decode(encoding, errors="replace")
        except (LookupError, TypeError):
            try:
                text = body.decode("cp1251", errors="replace")
            except Exception:
                text = body.decode("utf-8", errors="replace")
        return r.status_code, text
    finally:
        try:
            r.close()
        except Exception:
            pass


async def _cdp_fetch(url: str, ctx: Context | None) -> tuple[int, str]:
    """Tier-2: run in-page fetch inside Chrome over CDP."""

    async def _attempt() -> tuple[int, str]:
        async with _cdp_lock, open_page(f"{SITE_BASE}/", wait_ms=3000) as page:
            raw = await asyncio.wait_for(
                page.evaluate(
                    """async (args) => {
                    const res = await fetch(args.url, {
                        credentials: 'include',
                        headers: {
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'ru-RU,ru;q=0.9'
                        }
                    });
                    const reader = res.body.getReader();
                    let total = 0;
                    let chunks = [];
                    while (true) {
                        const {done, value} = await reader.read();
                        if (done) break;
                        total += value.length;
                        if (total > args.cap) {
                            return JSON.stringify({status: 0, text: 'BODY_CAP_EXCEEDED'});
                        }
                        chunks.push(value);
                    }
                    const buf = new Uint8Array(total);
                    let off = 0;
                    for (const c of chunks) { buf.set(c, off); off += c.length; }
                    let text = '';
                    try {
                        text = new TextDecoder('windows-1251').decode(buf);
                    } catch(e) {
                        text = new TextDecoder('utf-8').decode(buf);
                    }
                    return JSON.stringify({status: res.status, text: text, url: res.url});
                }""",
                    {"url": url, "cap": MAX_BODY_BYTES},
                ),
                timeout=30.0,
            )
        result = json.loads(raw) if isinstance(raw, str) else raw
        return result.get("status", 0), result.get("text", "")

    try:
        return await asyncio.wait_for(_attempt(), timeout=max(0.01, float(TIMEOUT)))
    except TimeoutError:
        return 0, f"CDP timeout after {TIMEOUT}s"


async def _fetch(url: str, ctx: Context | None) -> tuple[int, str, str]:
    """Fetch with cache and tier fallback (curl_cffi first if proxy configured, else CDP)."""
    cached = _cache.get(url)
    if cached is not None:
        status, body, tier = cached
        return status, body, tier

    await _polite_wait()

    proxy = _proxy()
    # Try tier-1 only if an explicit proxy is configured (datacenter IPs get blocked)
    if proxy:
        try:
            status, body = await asyncio.to_thread(_sync_curl_get, url, proxy)
            if status == 200 and ("bull-item" in body or "short-feedback" in body or "product" in body.lower()):
                _pacer.record_success()
                _cache.set(url, (status, body, "curl_cffi"))
                return status, body, "curl_cffi"
        except Exception as exc:
            if ctx:
                await ctx.debug(_redact(f"Drom tier-1 exception: {exc}; trying CDP"))

    try:
        status, body = await _cdp_fetch(url, ctx)
        if status == 200:
            _pacer.record_success()
            _cache.set(url, (status, body, "cdp"))
            return status, body, "cdp"
        if status in (401, 403, 429):
            _pacer.record_refusal()
            raise_tool_error(
                TransportDownError(f"baza.drom.ru returned HTTP {status} (blocked/rate-limit).", status_code=status)
            )
        return status, body, "cdp"
    except NavBlocked as exc:
        raise_tool_error(TransportDownError(f"baza.drom.ru CDP navigation blocked: {exc}", status_code=403))
    except Exception as exc:
        if isinstance(exc, ToolError):
            raise
        raise_tool_error(TransportDownError(f"baza.drom.ru CDP fetch failed: {_redact(str(exc))}"))


def _extract_item_id(raw: str) -> str | None:
    """Pull item ID from slug, URL or bare string."""
    raw = raw.strip()
    if raw.isdigit():
        return raw
    if re.match(r"^g\d{6,}$", raw, re.IGNORECASE):
        return raw.lower()
    m = _GOOD_ID_RE.search(raw)
    if m:
        return f"g{m.group(1)}"
    m = re.search(r"-(\d{6,})\.html", raw)
    if m:
        return m.group(1)
    m = _ITEM_ID_RE.search(raw)
    if m:
        return m.group(1)
    return None


def _extract_seller_id(raw: str) -> str | None:
    """Extract seller nickname/ID from URL or raw string."""
    raw = raw.strip().rstrip("/")
    if "/" in raw:
        parts = urllib.parse.urlsplit(raw)
        path = parts.path.strip("/")
        m = re.search(r"user/([^/]+)", path)
        if m:
            return m.group(1)
        # Last path component
        return path.split("/")[-1]
    return raw or None


def _attr_str(val: Any) -> str:
    """Safely coerce a BeautifulSoup attribute value to string."""
    if isinstance(val, list):
        return str(val[0]) if val else ""
    return str(val) if val is not None else ""


def _parse_search_html(html: str) -> tuple[list[dict[str, Any]], int | None]:
    """Parse search result listing items and total count from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, Any]] = []

    # Total count extraction
    total_count: int | None = None
    count_el = soup.select_one(".bull-count, .bulletins-count, .view_count, [data-role='bulletins-count']")
    if count_el and count_el.text:
        total_count = R.coerce_int(re.sub(r"[^\d]", "", count_el.text))
    if total_count is None:
        # Search page text e.g. "186 984 предложения"
        m = re.search(r"([\d\s\xa0]+)\s+предложен", html)
        if m:
            total_count = R.coerce_int(re.sub(r"[^\d]", "", m.group(1)))

    rows = soup.select(".bull-item, [data-bulletin-id]")
    for row in rows:
        bid = _attr_str(row.get("data-bulletin-id"))
        item_id: str | None = None
        if bid:
            item_id = f"g{bid[1:]}" if bid.startswith("-") else bid

        link_el = row.select_one("a.bulletinLink, .bull-item__self-link, a[name='bulletin']")
        title = link_el.text.strip() if link_el else None
        url = _attr_str(link_el.get("href")) if link_el else ""
        if url and url.startswith("/"):
            url = f"{SITE_BASE}{url}"
        if not item_id and url:
            item_id = _extract_item_id(url)

        price_el = row.select_one(".price-block__price, .priceCell, .finalPrice, .price")
        price_text = price_el.text.strip() if price_el else ""
        price_rub = R.coerce_price(price_text)

        old_price_el = row.select_one(".price-block__old-price, .old-price")
        old_price_rub = R.coerce_price(old_price_el.text.strip()) if old_price_el else None

        city_el = row.select_one(".bull-delivery__city, .bull-item__city, .bull-delivery")
        city = city_el.text.strip() if city_el else None

        delivery_el = row.select_one(".bull-delivery")
        delivery_info = delivery_el.text.strip() if delivery_el and delivery_el != city_el else None

        seller_el = row.select_one(".bull-item-info, .bull-item__seller, a[href*='/user/']")
        seller_name = seller_el.text.strip() if seller_el else None

        date_el = row.select_one(".date, .bull-item-info__value")
        posted_at = date_el.text.strip() if date_el else None

        annotation_el = row.select_one(".bull-item__annotation-row, .bull-item__annotation, .annotation")
        annotation = annotation_el.text.strip() if annotation_el else None

        # Image gallery
        gallery = row.select_one(".brief-image-gallery")
        image_urls: list[str] = []
        if gallery and gallery.get("data-images"):
            try:
                gallery_raw = _attr_str(gallery.get("data-images"))
                images_data = json.loads(gallery_raw)
                if isinstance(images_data, list):
                    for img in images_data:
                        if isinstance(img, dict) and "src" in img:
                            image_urls.append(str(img["src"]))
            except Exception:
                pass
        if not image_urls:
            img_tag = row.select_one("img")
            if img_tag and img_tag.get("src"):
                image_urls.append(_attr_str(img_tag.get("src")))

        condition: str | None = None
        row_text = row.text.lower()
        if "новый" in row_text:
            condition = "новый"
        elif "б/у" in row_text or "контрактн" in row_text:
            condition = "б/у"

        items.append(
            {
                "item_id": item_id,
                "title": title,
                "price_rub": price_rub,
                "old_price_rub": old_price_rub,
                "url": url,
                "city": city,
                "delivery_info": delivery_info,
                "seller_name": seller_name,
                "posted_at": posted_at,
                "images_count": len(image_urls),
                "image_urls": image_urls[:5],
                "annotation": annotation,
                "condition": condition,
            }
        )

    return items, total_count


def _parse_card_html(html: str, page_url: str, fallback_id: str | None = None) -> dict[str, Any]:
    """Parse product card details from JSON-LD Schema and HTML fallback."""
    soup = BeautifulSoup(html, "html.parser")

    title: str | None = None
    description: str | None = None
    price_rub: float | None = None
    price_currency: str = "RUB"
    is_available: bool | None = None
    condition: str | None = None
    brand: str | None = None
    images: list[str] = []
    breadcrumbs: list[str] = []

    # 1. Parse JSON-LD blocks
    for s in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(s.text)
            if not isinstance(data, dict):
                continue
            schema_type = data.get("@type")
            if schema_type == "Product":
                title = title or data.get("name")
                description = description or data.get("description")
                img_val = data.get("image")
                if isinstance(img_val, list):
                    images.extend(img_val)
                elif isinstance(img_val, str):
                    images.append(img_val)

                brand_val = data.get("brand")
                if isinstance(brand_val, dict):
                    brand = brand or brand_val.get("name")
                elif isinstance(brand_val, str):
                    brand = brand or brand_val

                offers = data.get("offers")
                if isinstance(offers, dict):
                    price_rub = price_rub or R.coerce_price(offers.get("price"))
                    price_currency = offers.get("priceCurrency") or price_currency
                    avail = offers.get("availability")
                    if avail:
                        is_available = "InStock" in avail
                    cond = offers.get("itemCondition")
                    if cond:
                        if "NewCondition" in cond:
                            condition = "новый"
                        elif "UsedCondition" in cond:
                            condition = "б/у"

            elif schema_type == "BreadcrumbList":
                items_list = data.get("itemListElement", [])
                if isinstance(items_list, list):
                    for b in items_list:
                        if isinstance(b, dict) and "name" in b:
                            breadcrumbs.append(b["name"])
        except Exception:
            continue

    # 2. HTML Fallbacks
    if not title:
        h1 = soup.select_one("h1, .subject, [data-bulletin-title]")
        title = h1.text.strip() if h1 else None

    if price_rub is None:
        price_el = soup.select_one(".price, .viewbull-summary__price, .viewbull-summary-price__value")
        if price_el:
            price_rub = R.coerce_price(price_el.text.strip())

    if is_available is None:
        body_text = soup.text
        if "В наличии" in body_text:
            is_available = True
        elif "Под заказ" in body_text:
            is_available = False

    # Auto parts specific fields: OEM, cross-numbers, compatibility
    oem: str | None = None
    m_oem = re.search(r"Номер:\s*([A-Za-z0-9_-]+)", soup.text)
    if m_oem:
        oem = m_oem.group(1)

    cross_numbers: list[str] = []
    oem_el = soup.select_one(".oem-numbers__list")
    if oem_el:
        oem_text = oem_el.text.strip()
        cross_numbers = [num.strip() for num in re.split(r"[\s,;]+", oem_text) if num.strip()]
        if not oem and cross_numbers:
            oem = cross_numbers[0]

    compatibility: list[str] = []
    for c_el in soup.select(".part-compatibility-item__list"):
        text = c_el.text.strip()
        if text:
            compatibility.append(text)

    # Seller info
    seller_out: DromSellerOut | None = None
    user_link = soup.select_one("a[href*='/user/']")
    if user_link:
        s_href = _attr_str(user_link.get("href"))
        s_id = _extract_seller_id(s_href)
        s_name = user_link.text.strip() or s_id
        rating_el = soup.select_one(".ratingPositive, .seller-info__rating")
        rating_score = R.coerce_price(rating_el.text.strip()) if rating_el else None

        review_link = soup.select_one("a[href*='/feedbacks']")
        reviews_count: int | None = None
        if review_link:
            m_rev = re.search(r"(\d+)", review_link.text)
            if m_rev:
                reviews_count = R.coerce_int(m_rev.group(1))

        seller_out = DromSellerOut(
            name=s_name,
            seller_id=s_id,
            rating_score=rating_score,
            reviews_count=reviews_count,
            profile_url=f"{SITE_BASE}/user/{s_id}/" if s_id else None,
        )

    # City & Address
    city: str | None = None
    address: str | None = None
    delivery_info: str | None = None

    summary_el = soup.select_one(".viewbull-summary")
    if summary_el:
        summary_text = summary_el.text
        for line in summary_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if "Самовывоз" in line or "ул." in line or "улица" in line:
                address = line
            elif "доставка" in line.lower():
                delivery_info = line

    return {
        "item_id": fallback_id or _extract_item_id(page_url),
        "title": title,
        "price_rub": price_rub,
        "price_currency": price_currency,
        "is_available": is_available,
        "condition": condition,
        "brand": brand,
        "oem": oem,
        "cross_numbers": cross_numbers,
        "compatibility": compatibility,
        "description": description,
        "city": city,
        "address": address,
        "delivery_info": delivery_info,
        "seller": seller_out,
        "images": images,
        "breadcrumbs": breadcrumbs,
        "url": page_url,
    }


def _parse_seller_html(profile_html: str, feedbacks_html: str | None, seller_id: str) -> dict[str, Any]:
    """Parse seller profile and customer feedbacks."""
    soup = BeautifulSoup(profile_html, "html.parser")

    name = soup.select_one(".user-info__name, h1, .header-title")
    display_name = name.text.strip() if name else seller_id

    rating_el = soup.select_one(".ratingPositive, .user-rating, [class*='rating']")
    rating_score = R.coerce_price(rating_el.text.strip()) if rating_el else None

    # Percent positive - search in seller text (not CSS)
    rating_percent: int | None = None
    m_pct = re.search(r"Рейтинг продавца[^\d]*\d+[^\d]*(\d+)%", profile_html)
    if not m_pct:
        m_pct = re.search(r"(\d+)%\s*положительн", profile_html)
    if m_pct:
        rating_percent = R.coerce_int(m_pct.group(1))

    # Reviews count
    reviews_count: int | None = None
    m_rc = re.search(r"(\d+)\s+отзыв", profile_html)
    if m_rc:
        reviews_count = R.coerce_int(m_rc.group(1))

    # Tenure
    tenure: str | None = None
    m_tenure = re.search(r"(\d+\s+г[ое][дл][а-я]*[,\s\d]*мес[а-я]*\s+на сайте)", profile_html)
    if m_tenure:
        tenure = m_tenure.group(1).strip()

    # Phone
    phone: str | None = None
    m_phone = re.search(r"(\+7\s*[\d\s-]{10,15})", profile_html)
    if m_phone:
        phone = m_phone.group(1).strip()

    # City
    city: str | None = None
    for c_cand in (
        "Хабаровск",
        "Владивосток",
        "Москва",
        "Новосибирск",
        "Иркутск",
        "Красноярск",
        "Челябинск",
        "Барнаул",
    ):
        if c_cand in profile_html:
            city = c_cand
            break

    # Offers count
    offers_count: int | None = None
    m_off = re.search(r"([\d\s\xa0]+)\s+предложен", profile_html)
    if m_off:
        offers_count = R.coerce_int(re.sub(r"[^\d]", "", m_off.group(1)))

    # Subscribers
    subscribers_count: int | None = None
    m_sub = re.search(r"(\d+)\s+подписчик", profile_html)
    if m_sub:
        subscribers_count = R.coerce_int(m_sub.group(1))

    # Feedbacks
    feedbacks_list: list[DromFeedbackOut] = []
    if feedbacks_html:
        fb_soup = BeautifulSoup(feedbacks_html, "html.parser")
        fb_elements = fb_soup.select(".short-feedback")
        for fb in fb_elements:
            fb_text = fb.select_one(".short-feedback__text")
            fb_date = fb.select_one(".date, time")
            fb_author = fb.select_one(".user-badge, .short-feedback__author")
            fb_grade = fb.select_one("[class*='grade'], [class*='rating'], [class*='positive']")
            feedbacks_list.append(
                DromFeedbackOut(
                    text=fb_text.text.strip() if fb_text else fb.text.strip(),
                    date=fb_date.text.strip() if fb_date else None,
                    author=fb_author.text.strip() if fb_author else None,
                    grade=fb_grade.text.strip() if fb_grade else None,
                )
            )

    seller_out = DromSellerOut(
        name=display_name,
        seller_id=seller_id,
        rating_score=rating_score,
        rating_percent=rating_percent,
        reviews_count=reviews_count,
        tenure=tenure,
        phone=phone,
        city=city,
        profile_url=f"{SITE_BASE}/user/{seller_id}/",
    )

    return {
        "seller": seller_out,
        "offers_count": offers_count,
        "subscribers_count": subscribers_count,
        "feedbacks": feedbacks_list[:20],
    }


def _build_search_url(
    query: str,
    page: int,
    city: str | None,
    category: str | None,
    condition: str | None,
    sort_by: str,
    in_stock_only: bool,
    with_photos_only: bool,
) -> str:
    """Construct search URL for baza.drom.ru with cp1251 encoded query."""
    parts = [SITE_BASE]
    if city:
        city_slug = city.strip().lower().strip("/")
        parts.append(city_slug)
    if category:
        cat_slug = category.strip().strip("/")
        parts.append(cat_slug)
    else:
        parts.append("sell_spare_parts")

    base_path = "/".join(parts) + "/"

    encoded_q = _encode_cp1251_query(query)
    params: list[str] = [f"query={encoded_q}"]

    if page > 1:
        params.append(f"page={page}")
    if condition == "new":
        params.append("condition%5B%5D=new")
    elif condition == "used":
        params.append("condition%5B%5D=used")
    if in_stock_only:
        params.append("goodPresentState%5B%5D=present")
    if with_photos_only:
        params.append("hasImages=on")
    if sort_by == "price_asc":
        params.append("sortBy=pricea")
    elif sort_by == "price_desc":
        params.append("sortBy=priced")

    return f"{base_path}?{'&'.join(params)}"


@mcp.tool(
    name="drom_search",
    annotations=ToolAnnotations(
        title="baza.drom.ru Search",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def drom_search(
    query: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description="Search text or OEM number, e.g. 'масло toyota 0w20' or '04465-33470'",
        ),
    ],
    page: Annotated[int, Field(ge=1, le=100, description="Result page (1-based)")] = 1,
    city: Annotated[
        str | None,
        Field(
            description="City slug (e.g. 'vladivostok', 'moskva', 'khabarovsk', 'novosibirsk') or None for all cities"
        ),
    ] = None,
    category: Annotated[
        str | None, Field(description="Catalog section, e.g. 'sell_spare_parts', 'wheel', 'chemistry/motoroil'")
    ] = None,
    condition: Annotated[
        Literal["all", "new", "used"] | None, Field(description="Condition filter: 'new', 'used' or None/all")
    ] = None,
    sort_by: Annotated[Literal["relevance", "price_asc", "price_desc"], Field(description="Sort order")] = "relevance",
    in_stock_only: Annotated[bool, Field(description="Filter items currently in stock")] = False,
    with_photos_only: Annotated[bool, Field(description="Filter items with photos")] = False,
    ctx: Context | None = None,
) -> DromSearchResponse:
    """Search auto parts, wheels, oils and listings on baza.drom.ru.

    ## Return Format

    DromSearchResponse: {status, query, page, city, tier_used, count, total_count, items[], meta}.
    Items carry bulletin_id, title, price_rub (None when no price — never 0), url, city, seller_name,
    photo_url, has_photo, is_new, published_at.

    ## Error Format

    ToolError: BadRequestError on invalid query or parameters; TransportDownError on
    network failure, timeout or non-200 responses.
    """
    effective_city = city or _settings.default_city or None
    url = _build_search_url(
        query=query,
        page=page,
        city=effective_city,
        category=category,
        condition=condition,
        sort_by=sort_by,
        in_stock_only=in_stock_only,
        with_photos_only=with_photos_only,
    )

    status, html, tier = await _fetch(url, ctx)
    if status != 200:
        raise_tool_error(TransportDownError(f"baza.drom.ru search returned HTTP {status} via {tier}."))

    items_raw, total_count = _parse_search_html(html)

    items_out = [DromSearchItemOut(**it) for it in items_raw]
    res = DromSearchResponse(
        status="success",
        query=query,
        page=page,
        city=effective_city,
        tier_used=tier,
        count=len(items_out),
        total_count=total_count,
        items=items_out,
    )
    warnings: list[str] = []
    if not items_out and total_count not in (0, None):
        warnings.append("empty_items_with_nonzero_total")
    attached = R.attach_meta(res.model_dump(by_alias=True, exclude={"meta"}), warnings, source="drom_search")
    res.meta = MetaOut(**attached["_meta"])
    return res


@mcp.tool(
    name="drom_card",
    annotations=ToolAnnotations(
        title="baza.drom.ru Item Card",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def drom_card(
    url_or_id: Annotated[
        str, Field(min_length=1, description="Item ID (e.g. '137849325', 'g12841036510') or full baza.drom.ru URL")
    ],
    ctx: Context | None = None,
) -> DromCardResponse:
    """Get detailed item information from baza.drom.ru by ID or URL.

    Reads Schema.org JSON-LD (Product, Offer, BreadcrumbList) and HTML attributes.

    ## Return Format

    DromCardResponse: {status, bulletin_id, url, title, price_rub (None if unpriced — never 0),
    description, condition, availability, brand, oem_numbers, city, seller, photos,
    breadcrumbs, tier_used, meta}.

    ## Error Format

    ToolError: BadRequestError on invalid id/URL; NotFoundError on HTTP 404;
    TransportDownError on network failure or non-200 responses.
    """
    cleaned = url_or_id.strip()
    item_id = _extract_item_id(cleaned)
    if not item_id:
        raise_tool_error(BadRequestError(f"Could not extract a valid Drom item ID from '{cleaned}'."))

    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        target_url = cleaned
    elif item_id.startswith("g"):
        target_url = f"{SITE_BASE}/{item_id}.html"
    else:
        target_url = f"{SITE_BASE}/bulletin/{item_id}.html"

    status, html, tier = await _fetch(target_url, ctx)
    if status == 404:
        raise_tool_error(NotFoundError(f"baza.drom.ru item '{item_id}' not found (404)."))
    if status != 200:
        raise_tool_error(TransportDownError(f"baza.drom.ru card fetch failed: HTTP {status} via {tier}."))

    card_data = _parse_card_html(html, target_url, fallback_id=item_id)
    card_data["tier_used"] = tier

    res = DromCardResponse(**card_data)
    warnings: list[str] = []
    if not res.title:
        warnings.append("missing_title")
    if res.price_rub is None and res.is_available:
        warnings.append("available_without_price")
    attached = R.attach_meta(res.model_dump(by_alias=True, exclude={"meta"}), warnings, source="drom_card")
    res.meta = MetaOut(**attached["_meta"])
    return res


@mcp.tool(
    name="drom_seller",
    annotations=ToolAnnotations(
        title="baza.drom.ru Seller Profile",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def drom_seller(
    seller_id_or_url: Annotated[
        str, Field(min_length=1, description="Seller nickname/ID or profile URL, e.g. 'AUTORAZBORKADV'")
    ],
    feedbacks_page: Annotated[int, Field(ge=1, le=10, description="Feedbacks page number")] = 1,
    ctx: Context | None = None,
) -> DromSellerResponse:
    """Get seller profile, rating, and customer feedbacks on baza.drom.ru.

    ## Return Format

    DromSellerResponse: {status, seller_id, url, tier_used, seller (name, rating,
    feedbacks_count, registration_year, city, active_bulletins_count), feedbacks[], meta}.

    ## Error Format

    ToolError: BadRequestError on empty seller ID; NotFoundError on HTTP 404;
    TransportDownError on network failure or non-200 responses.
    """
    seller_id = _extract_seller_id(seller_id_or_url)
    if not seller_id:
        raise_tool_error(BadRequestError(f"Invalid seller identifier '{seller_id_or_url}'."))

    profile_url = f"{SITE_BASE}/user/{seller_id}/"
    feedbacks_url = f"{SITE_BASE}/user/{seller_id}/feedbacks?role=participant&page={feedbacks_page}"

    p_status, p_html, p_tier = await _fetch(profile_url, ctx)
    if p_status == 404:
        raise_tool_error(NotFoundError(f"baza.drom.ru seller '{seller_id}' not found (404)."))
    if p_status != 200:
        raise_tool_error(TransportDownError(f"Failed to fetch seller profile: HTTP {p_status} via {p_tier}."))

    f_html: str | None = None
    try:
        f_status, f_html_text, _ = await _fetch(feedbacks_url, ctx)
        if f_status == 200:
            f_html = f_html_text
    except Exception:
        pass

    seller_data = _parse_seller_html(p_html, f_html, seller_id)
    seller_data["tier_used"] = p_tier

    res = DromSellerResponse(**seller_data)
    warnings: list[str] = []
    if not res.seller or not res.seller.name:
        warnings.append("missing_seller_name")
    attached = R.attach_meta(res.model_dump(by_alias=True, exclude={"meta"}), warnings, source="drom_seller")
    res.meta = MetaOut(**attached["_meta"])
    return res


# CLI-only drift canary: ``marketplace-mcp doctor`` imports and calls drom_selfcheck()
# directly. It is deliberately NOT registered as an MCP tool — selfchecks are
# operator diagnostics, and their input/output schemas would be billed in every
# client request.
async def drom_selfcheck(ctx: Context | None = None) -> DromSelfcheckResponse:
    """Probe baza.drom.ru search and card extraction to detect parser drift."""
    checks: dict[str, Any] = {}

    # 1. Search probe
    search_url = _build_search_url("масло 0w20", 1, None, None, None, "relevance", False, False)
    try:
        status, html, tier = await _fetch(search_url, ctx)
        if status != 200:
            checks["search"] = R.selfcheck_entry(
                "inconclusive",
                baseline="search",
                reason=f"HTTP {status} via {tier}",
            )
        else:
            items, _ = _parse_search_html(html)
            if items:
                sig = set(R.shape_signature({"items": items}))
                missing = missing_required_keys(sig, SEARCH_REQUIRED_KEYS)
                if missing:
                    checks["search"] = R.selfcheck_entry(
                        "drift",
                        baseline="search",
                        reason=f"Missing required keys: {missing}",
                    )
                else:
                    checks["search"] = R.selfcheck_entry(
                        "healthy",
                        baseline="search",
                    )
            else:
                checks["search"] = R.selfcheck_entry(
                    "drift",
                    baseline="search",
                    reason="Search returned 0 items",
                )
    except Exception as exc:
        checks["search"] = R.selfcheck_entry(
            "inconclusive",
            baseline="search",
            reason=_redact(str(exc))[:120],
        )

    # 2. Card probe
    card_url = f"{SITE_BASE}/g15237311871.html"
    try:
        c_status, c_html, c_tier = await _fetch(card_url, ctx)
        if c_status != 200:
            checks["card"] = R.selfcheck_entry(
                "inconclusive",
                baseline="card",
                reason=f"HTTP {c_status} via {c_tier}",
            )
        else:
            card_dict = _parse_card_html(c_html, card_url, fallback_id="g15237311871")
            sig = set(R.shape_signature(card_dict))
            missing = missing_required_keys(sig, CARD_REQUIRED_KEYS)
            if missing:
                checks["card"] = R.selfcheck_entry(
                    "drift",
                    baseline="card",
                    reason=f"Missing required keys: {missing}",
                )
            else:
                checks["card"] = R.selfcheck_entry(
                    "healthy",
                    baseline="card",
                )
    except Exception as exc:
        checks["card"] = R.selfcheck_entry(
            "inconclusive",
            baseline="card",
            reason=_redact(str(exc))[:120],
        )

    result_dict = R.selfcheck_result(
        "drom",
        checks,
        required=("search", "card"),
        server_version=SERVER_VERSION,
        server_started_at=SERVER_STARTED_AT,
        process_id=None,
    )
    return DromSelfcheckResponse(**result_dict)


apply_compact_output_schemas(mcp)
