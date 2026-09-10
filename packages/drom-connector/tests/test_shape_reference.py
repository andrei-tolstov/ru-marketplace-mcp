"""Test shape reference helpers and required keys."""

from __future__ import annotations

from drom_connector.shape_reference import SEARCH_REQUIRED_KEYS, missing_required_keys


def test_missing_required_keys_detects_empty():
    missing = missing_required_keys(set(), SEARCH_REQUIRED_KEYS)
    assert len(missing) == len(SEARCH_REQUIRED_KEYS)


def test_missing_required_keys_detects_present():
    sig = {
        "items[].item_id:str",
        "items[].title:str",
        "items[].price_rub:float",
        "items[].url:str",
    }
    missing = missing_required_keys(sig, SEARCH_REQUIRED_KEYS)
    assert missing == []


def test_missing_required_keys_partial():
    sig = {
        "items[].item_id:str",
        "items[].title:str",
    }
    missing = missing_required_keys(sig, SEARCH_REQUIRED_KEYS)
    assert "items[].price_rub" in missing
    assert "items[].url" in missing
