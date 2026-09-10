"""Pydantic output models for the baza.drom.ru MCP connector.

Every tool returns a typed Pydantic model instead of a raw dict. The ``meta``
field is populated from the ``_meta`` key that ``resilience.attach_meta``
writes, and serializes back to ``meta`` on the wire.
"""

from __future__ import annotations

from mcp_core.models import MetaOutBase, SelfCheckEntryBase, SelfCheckResponseBase
from pydantic import BaseModel, ConfigDict, Field


class MetaOut(MetaOutBase):
    """baza.drom.ru carries the shared envelope unchanged."""


class DromSearchItemOut(BaseModel):
    item_id: str | None = Field(default=None, description="Item ID (e.g. '137849325' or 'g12841036510').")
    title: str | None = Field(default=None, description="Listing title.")
    price_rub: float | None = Field(default=None, description="Price in rubles; None when listing has no price.")
    old_price_rub: float | None = Field(default=None, description="Strikethrough / previous price if discounted.")
    url: str | None = Field(default=None, description="Canonical baza.drom.ru URL.")
    city: str | None = Field(default=None, description="City / location.")
    delivery_info: str | None = Field(default=None, description="Delivery or shipping terms.")
    seller_name: str | None = Field(default=None, description="Seller display name or company.")
    posted_at: str | None = Field(default=None, description="Publication time or date string.")
    images_count: int = Field(default=0, description="Count of images.")
    image_urls: list[str] = Field(default_factory=list, description="Image thumbnail URLs.")
    annotation: str | None = Field(default=None, description="Specs or characteristics summary snippet.")
    condition: str | None = Field(default=None, description="Condition: 'новый', 'б/у' or None.")


class DromSearchResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="success", description="Response status: success or error.")
    query: str = Field(default="", description="Search query text.")
    page: int = Field(default=1, description="Result page number.")
    city: str | None = Field(default=None, description="City filter applied.")
    tier_used: str | None = Field(default=None, description="Fetch tier used: curl_cffi, cdp, cache.")
    count: int = Field(default=0, description="Number of items returned on this page.")
    total_count: int | None = Field(default=None, description="Total matches reported for the query.")
    items: list[DromSearchItemOut] = Field(default_factory=list, description="Search result items.")
    meta: MetaOut = Field(default_factory=MetaOut, alias="_meta", description="Validation metadata.")


class DromSellerOut(BaseModel):
    name: str | None = Field(default=None, description="Seller display name or nickname.")
    seller_id: str | None = Field(default=None, description="Seller ID or nickname from URL.")
    rating_score: float | None = Field(default=None, description="Positive rating count or score.")
    rating_percent: int | None = Field(default=None, description="Percentage of positive ratings (e.g. 100).")
    reviews_count: int | None = Field(default=None, description="Total review count.")
    tenure: str | None = Field(default=None, description="Time on site (e.g. '3 года, 6 месяцев на сайте').")
    phone: str | None = Field(default=None, description="Public phone number if displayed.")
    city: str | None = Field(default=None, description="Seller home city.")
    address: str | None = Field(default=None, description="Seller physical address / pickup point.")
    profile_url: str | None = Field(default=None, description="Full profile URL.")


class DromFeedbackOut(BaseModel):
    text: str | None = Field(default=None, description="Feedback text.")
    date: str | None = Field(default=None, description="Feedback date.")
    author: str | None = Field(default=None, description="Author nickname.")
    grade: str | None = Field(default=None, description="Grade / rating tag.")


class DromCardResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="success", description="Response status: success or error.")
    item_id: str | None = Field(default=None, description="Item ID.")
    title: str | None = Field(default=None, description="Item title.")
    price_rub: float | None = Field(default=None, description="Price in rubles; None when listing has no price.")
    price_currency: str = Field(default="RUB", description="Currency code.")
    is_available: bool | None = Field(default=None, description="Whether the item is in stock.")
    condition: str | None = Field(default=None, description="Item condition (новый, б/у, контрактный).")
    brand: str | None = Field(default=None, description="Brand / manufacturer.")
    oem: str | None = Field(default=None, description="OEM or part number.")
    cross_numbers: list[str] = Field(default_factory=list, description="Cross/interchange OEM numbers.")
    compatibility: list[str] = Field(default_factory=list, description="Car compatibility (bodies, engines).")
    description: str | None = Field(default=None, description="Full description text.")
    city: str | None = Field(default=None, description="City / location.")
    address: str | None = Field(default=None, description="Pickup address.")
    delivery_info: str | None = Field(default=None, description="Delivery and payment terms.")
    seller: DromSellerOut | None = Field(default=None, description="Seller information.")
    images: list[str] = Field(default_factory=list, description="Full resolution image URLs.")
    breadcrumbs: list[str] = Field(default_factory=list, description="Category breadcrumb chain.")
    url: str = Field(default="", description="Canonical baza.drom.ru URL.")
    tier_used: str = Field(default="", description="Fetch tier used.")
    meta: MetaOut = Field(default_factory=MetaOut, alias="_meta", description="Validation metadata.")


class DromSellerResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="success", description="Response status: success or error.")
    seller: DromSellerOut | None = Field(default=None, description="Seller profile info.")
    offers_count: int | None = Field(default=None, description="Active listings count.")
    subscribers_count: int | None = Field(default=None, description="Followers count.")
    feedbacks: list[DromFeedbackOut] = Field(default_factory=list, description="Recent customer feedbacks.")
    tier_used: str = Field(default="", description="Fetch tier used.")
    meta: MetaOut = Field(default_factory=MetaOut, alias="_meta", description="Validation metadata.")


class DromSelfcheckCheckOut(SelfCheckEntryBase):
    ok: bool | None = Field(default=None, description="Boolean health summary if applicable.")
    baseline: str = Field(default="", description="Baseline identifier used for comparison.")
    reason: str | None = Field(default=None, description="Reason code for non-healthy verdicts.")


class DromSelfcheckResponse(SelfCheckResponseBase):
    healthy: bool | None = Field(default=None, description="Whether all checks are healthy.")
    checks: dict[str, DromSelfcheckCheckOut] = Field(default_factory=dict, description="Per-subcheck results.")
