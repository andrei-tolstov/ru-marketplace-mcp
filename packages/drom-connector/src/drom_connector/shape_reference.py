"""Reference shape signatures for baza.drom.ru extractors."""

from __future__ import annotations

SEARCH_REQUIRED_KEYS: tuple[str, ...] = (
    "items[].item_id",
    "items[].title",
    "items[].price_rub",
    "items[].url",
)

CARD_REQUIRED_KEYS: tuple[str, ...] = (
    "item_id",
    "title",
    "price_rub",
    "url",
)


def missing_required_keys(signature: set[str], required_keys: tuple[str, ...]) -> list[str]:
    """Return required paths that have no matching entry in the signature."""
    missing: list[str] = []
    for req in required_keys:
        prefix = req + ":"
        if not any(s.startswith(prefix) for s in signature):
            missing.append(req)
    return missing
