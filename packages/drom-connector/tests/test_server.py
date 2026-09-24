"""Offline tests for baza.drom.ru connector."""

from __future__ import annotations

import pytest
from drom_connector import server
from fastmcp.exceptions import ToolError
from mcp.types import ImageContent, TextContent


@pytest.fixture(autouse=True)
def _clear_cache():
    server._cache._data.clear()


# ------------------------------------------------------------------ helpers ----


def test_extract_item_id_numeric():
    assert server._extract_item_id("137849325") == "137849325"
    assert server._extract_item_id("  1234567  ") == "1234567"


def test_extract_item_id_goods():
    assert server._extract_item_id("g12841036510") == "g12841036510"
    assert server._extract_item_id("G12841036510") == "g12841036510"
    assert server._extract_item_id("/g12841036510.html") == "g12841036510"
    assert (
        server._extract_item_id("https://baza.drom.ru/khabarovsk/sell_spare_parts/item-g12841036510.html")
        == "g12841036510"
    )


def test_extract_item_id_url():
    url = "https://baza.drom.ru/vladivostok/chemistry/motoroil/maslo-motornoe-toyota-0w20-200l-137849325.html"
    assert server._extract_item_id(url) == "137849325"


def test_extract_seller_id():
    assert server._extract_seller_id("AUTORAZBORKADV") == "AUTORAZBORKADV"
    assert server._extract_seller_id("https://baza.drom.ru/user/AUTORAZBORKADV/") == "AUTORAZBORKADV"
    assert server._extract_seller_id("https://baza.drom.ru/user/AUTORAZBORKADV/feedbacks") == "AUTORAZBORKADV"


def test_encode_cp1251_query():
    encoded = server._encode_cp1251_query("масло")
    assert "%ec%e0%f1%eb%ee" in encoded.lower()


def test_build_search_url():
    url = server._build_search_url(
        query="колодки",
        page=2,
        city="vladivostok",
        category="sell_spare_parts",
        condition="new",
        sort_by="price_asc",
        in_stock_only=True,
        with_photos_only=True,
    )
    assert "https://baza.drom.ru/vladivostok/sell_spare_parts/" in url
    assert "page=2" in url
    assert "condition%5B%5D=new" in url
    assert "sortBy=pricea" in url
    assert "goodPresentState%5B%5D=present" in url
    assert "hasImages=on" in url


# ------------------------------------------------------------------ parsing ----


def test_parse_search_html(search_html):
    items, total = server._parse_search_html(search_html)
    assert len(items) > 0
    assert items[0]["item_id"] is not None
    assert items[0]["title"] is not None
    assert items[0]["price_rub"] is not None
    assert items[0]["price_rub"] > 0
    assert total is not None and total > 0


def test_parse_card_oil_html(card_oil_html):
    url = "https://baza.drom.ru/vladivostok/chemistry/motoroil/maslo-motornoe-toyota-0w20-200l-137849325.html"
    card = server._parse_card_html(card_oil_html, url)
    assert "Toyota 0w20" in (card["title"] or "")
    assert card["price_rub"] == 185000.0
    assert card["price_currency"] == "RUB"
    assert card["is_available"] is True
    assert card["brand"] == "Toyota"
    assert len(card["breadcrumbs"]) > 0


def test_parse_card_part_html(card_part_html):
    url = "https://baza.drom.ru/khabarovsk/sell_spare_parts/kolodki-tormoznye-toyota-camry-0446533470-acv40-2azfe-g12841036510.html"
    card = server._parse_card_html(card_part_html, url)
    assert "Колодки тормозные" in (card["title"] or "")
    assert card["price_rub"] == 2050.0
    assert card["oem"] == "0446533470" or "0446533470" in card["cross_numbers"]
    assert card["condition"] == "новый"
    assert card["seller"] is not None
    assert card["seller"].name == "AUTORAZBORKADV"
    assert len(card["compatibility"]) > 0


def test_parse_seller_html(seller_html, feedbacks_html):
    data = server._parse_seller_html(seller_html, feedbacks_html, "AUTORAZBORKADV")
    seller = data["seller"]
    assert seller.name == "AUTORAZBORKADV"
    assert seller.rating_score == 273.0
    assert seller.rating_percent == 100
    assert seller.city == "Хабаровск"
    assert len(data["feedbacks"]) > 0
    assert data["feedbacks"][0].text is not None


# ------------------------------------------------------------------ tools ----


@pytest.mark.asyncio
async def test_drom_search_tool(monkeypatch, search_html):
    async def fake_fetch(url, ctx):
        return 200, search_html, "cdp"

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    resp = await server.drom_search(query="масло", city="vladivostok")
    assert resp.status == "success"
    assert resp.count > 0
    assert resp.items[0].price_rub is not None
    assert resp.tier_used == "cdp"
    assert resp.meta.healthy is True


@pytest.mark.asyncio
async def test_drom_card_tool(monkeypatch, card_part_html):
    async def fake_fetch(url, ctx):
        return 200, card_part_html, "cdp"

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    resp = await server.drom_card("g12841036510")
    assert resp.status == "success"
    assert resp.item_id == "g12841036510"
    assert resp.price_rub == 2050.0
    assert resp.oem == "0446533470" or "0446533470" in resp.cross_numbers
    assert resp.meta.healthy is True


@pytest.mark.asyncio
async def test_drom_card_invalid_id():
    with pytest.raises(ToolError):
        await server.drom_card("  ")


@pytest.mark.asyncio
async def test_drom_seller_tool(monkeypatch, seller_html, feedbacks_html):
    async def fake_fetch(url, ctx):
        if "feedbacks" in url:
            return 200, feedbacks_html, "cdp"
        return 200, seller_html, "cdp"

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    resp = await server.drom_seller("AUTORAZBORKADV")
    assert resp.status == "success"
    assert resp.seller is not None
    assert resp.seller.name == "AUTORAZBORKADV"
    assert len(resp.feedbacks) > 0
    assert resp.meta.healthy is True


@pytest.mark.asyncio
async def test_drom_selfcheck_healthy(monkeypatch, search_html, card_part_html):
    async def fake_fetch(url, ctx):
        if "g15237311871" in url:
            return 200, card_part_html, "cdp"
        return 200, search_html, "cdp"

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    resp = await server.drom_selfcheck()
    assert resp.healthy is True
    assert resp.checks["search"].ok is True
    assert resp.checks["card"].ok is True


# ------------------------------------------------------------- photo inspection ----


def test_sniff_image_mime():
    assert server._sniff_image_mime(b"\xff\xd8\xff\xe0", "image/jpeg") == "image/jpeg"
    assert server._sniff_image_mime(b"\x89PNG\r\n\x1a\n\x00", None) == "image/png"
    assert server._sniff_image_mime(b"RIFF\x00\x00\x00\x00WEBPVP8", None) == "image/webp"
    assert server._sniff_image_mime(b"GIF89a\x01\x00", None) == "image/gif"
    assert server._sniff_image_mime(b"unknown bytes", None) == "image/jpeg"


@pytest.mark.asyncio
async def test_download_photo_high_res_and_fallback(monkeypatch):
    calls: list[str] = []

    def fake_sync_download(url, proxy=None):
        calls.append(url)
        if "_full" in url:
            # Simulate high-res 404/failure
            return None
        if "_bulletin" in url:
            return b"\xff\xd8\xff\xe0test_jpeg", "image/jpeg"
        return None

    async def fake_cdp_download(url):
        return None

    monkeypatch.setattr(server, "_sync_download_photo", fake_sync_download)
    monkeypatch.setattr(server, "_cdp_download_photo", fake_cdp_download)
    monkeypatch.setattr(server, "_proxy", lambda: None)

    res = await server._download_photo("https://static.baza.drom.ru/drom/1786204363632_bulletin", high_res=True)
    assert res is not None
    data, mime = res
    assert data == b"\xff\xd8\xff\xe0test_jpeg"
    assert mime == "image/jpeg"
    assert len(calls) == 2
    assert "_full" in calls[0]
    assert "_bulletin" in calls[1]


@pytest.mark.asyncio
async def test_download_photo_cdp_fallback(monkeypatch):
    monkeypatch.setattr(server, "_sync_download_photo", lambda url, proxy=None: None)

    async def fake_cdp_download(url):
        return b"\x89PNG\r\n\x1a\nfrom_cdp", "image/png"

    monkeypatch.setattr(server, "_cdp_download_photo", fake_cdp_download)
    monkeypatch.setattr(server, "_proxy", lambda: None)

    res = await server._download_photo("https://static.baza.drom.ru/drom/photo_test", high_res=False)
    assert res is not None
    data, mime = res
    assert data == b"\x89PNG\r\n\x1a\nfrom_cdp"
    assert mime == "image/png"


@pytest.mark.asyncio
async def test_drom_card_photos_tool(monkeypatch, card_part_html):
    async def fake_fetch(url, ctx):
        return 200, card_part_html, "cdp"

    async def fake_download(url, high_res=True, ctx=None):
        return b"\xff\xd8\xff\xe0fake_bytes", "image/jpeg"

    monkeypatch.setattr(server, "_fetch", fake_fetch)
    monkeypatch.setattr(server, "_download_photo", fake_download)

    contents = await server.drom_card_photos("g12841036510", max_photos=2)
    assert len(contents) >= 2
    assert isinstance(contents[0], TextContent)
    assert "Колодки тормозные" in contents[0].text
    assert "Обязательный регламент визуального анализа" in contents[0].text
    assert "0446533470" in contents[0].text

    for item in contents[1:]:
        assert isinstance(item, ImageContent)
        assert item.type == "image"
        assert item.mimeType == "image/jpeg"
        assert len(item.data) > 0


@pytest.mark.asyncio
async def test_drom_card_photos_direct_url(monkeypatch):
    async def fake_download(url, high_res=True, ctx=None):
        return b"\x89PNG\r\n\x1a\nfake_png", "image/png"

    monkeypatch.setattr(server, "_download_photo", fake_download)

    direct_url = "https://static.baza.drom.ru/drom/1786204363632_bulletin.jpg"
    contents = await server.drom_card_photos(direct_url)
    assert len(contents) == 2
    assert isinstance(contents[0], TextContent)
    assert "Прямое фото автозапчасти Drom" in contents[0].text
    assert isinstance(contents[1], ImageContent)
    assert contents[1].mimeType == "image/png"


@pytest.mark.asyncio
async def test_drom_card_photos_no_images(monkeypatch):
    html_without_images = "<html><body><h1>Гайка колесная</h1><div class='price'>100</div></body></html>"

    async def fake_fetch(url, ctx):
        return 200, html_without_images, "cdp"

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    contents = await server.drom_card_photos("123456")
    assert len(contents) == 1
    assert isinstance(contents[0], TextContent)
    assert "отсутствуют прикрепленные фотографии" in contents[0].text


@pytest.mark.asyncio
async def test_drom_card_photos_download_failure(monkeypatch, card_part_html):
    async def fake_fetch(url, ctx):
        return 200, card_part_html, "cdp"

    async def fake_download_fail(url, high_res=True, ctx=None):
        return None

    monkeypatch.setattr(server, "_fetch", fake_fetch)
    monkeypatch.setattr(server, "_download_photo", fake_download_fail)

    with pytest.raises(ToolError):
        await server.drom_card_photos("g12841036510")
