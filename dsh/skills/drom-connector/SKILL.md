---
name: drom-connector
description: Use this skill when the operator needs automotive classifieds and spare parts data from baza.drom.ru — search auto parts, tires, wheels, oils, listing cards, or seller reputation and feedbacks. Trigger on Russian queries like "найди на дроме", "запчасти дром", "baza drom", "база дром", "цена на дром", "продавец на дроме", or mentions of baza.drom.ru. Uses Chrome over CDP or RU residential proxy.
---

# baza.drom.ru Connector

Connects to baza.drom.ru, Russia's primary automotive marketplace and classifieds
platform: new, used, and contractual auto parts, tires, wheels, car oils, fluids,
and general bulletins.

baza.drom.ru uses charset=windows-1251 for its HTML and canonical query strings.
Two access tiers:
- Tier 2: in-page fetch within the operator's running Chrome via CDP (works from
  datacenter IPs without firewall block)
- Tier 1: impersonated HTTPS (curl_cffi) when an RU residential proxy is configured

## When to use
- Search auto parts and accessories with optional filters (city, price range, sorting, new/used, with photo)
- Product or bulletin details: title, price, description, photos, brand, OEM numbers, condition, stock availability, breadcrumbs
- Seller reputation, verification status, rating, active bulletin count, and recent buyer feedbacks

## Tools available
- `drom_search(query, page, city, min_price, max_price, sort, has_photo, is_new)` — search listings. price_rub is None for listings without a specified price (e.g. negotiable, exchange) — never 0.
- `drom_card(item_id_or_url)` — detailed card info: price, description, attributes, photos, seller summary, breadcrumbs
- `drom_seller(seller_id_or_url)` — seller rating, feedbacks count, registration year, city, active bulletin count, recent reviews

**Not an MCP tool:** `drom_selfcheck()` is a tri-state drift canary. It is CLI-only — `marketplace-mcp doctor` runs every connector's canary at once.

## What search and card payloads carry
- **`bulletin_id`**: can be numeric (for regular ads, e.g. `137849325`) or catalog goods identifier with a leading `g` (e.g. `g12841036510`).
- **`price_rub`**: extracted as a normalized float. When price is not specified, it is `None`, never 0.
- **`breadcrumbs`**: hierarchical category navigation from schema.org JSON-LD or DOM breadcrumbs trail.
- **`seller`**: on card and seller pages, carries verified status, rating, reviews count, and active bulletin count.

## Gotchas
- baza.drom.ru serves pages in Windows-1251. The connector handles URL percent-encoding and HTML decoding automatically.
- Datacenter IPs are dropped or blocked by WAF over direct TLS. Tier 2 CDP Chrome session is the default and recommended mode.
- Paging: baza.drom.ru pagination uses `?page=N`. Sorting options: `relevance`, `price_asc`, `price_desc`, `date_desc`.

## DSH activation

In DeepSeek Harness, the default profile exposes only `compare_prices` and
`compare_sources` through the cheap compare mount. Per-marketplace tools and
`marketplace_sources` require `RU_MARKETPLACE_MCP_FULL=1` and a profile restart;
do not call them in the default mode.
