"""Shared fixtures for drom-connector tests."""

from __future__ import annotations

import pathlib

import pytest

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def search_html() -> str:
    return (FIXTURES_DIR / "search_live.html").read_text(encoding="utf-8")


@pytest.fixture
def card_oil_html() -> str:
    return (FIXTURES_DIR / "card_oil_live.html").read_text(encoding="utf-8")


@pytest.fixture
def card_part_html() -> str:
    return (FIXTURES_DIR / "card_part_live.html").read_text(encoding="utf-8")


@pytest.fixture
def seller_html() -> str:
    return (FIXTURES_DIR / "seller_live.html").read_text(encoding="utf-8")


@pytest.fixture
def feedbacks_html() -> str:
    return (FIXTURES_DIR / "feedbacks_live.html").read_text(encoding="utf-8")
