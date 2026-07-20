"""Models for scraped data validation and transformation."""

from __future__ import annotations

from pydantic import Field, field_validator, BaseModel
from hashlib import sha256
import json
from typing import Any, List, Optional
from datetime import datetime


class PriceBlock(BaseModel):
    """Represents a price block in the scraped data."""

    currency: str = "$"
    original_price: Optional[float] = None
    discount_price: Optional[float] = None
    current_price: Optional[float] = None
    you_save_amount: Optional[float] = None
    you_save_percent: Optional[int] = None
    is_bargain_price: bool = False


class ShippingInfo(BaseModel):
    """Represents shipping information in the scraped data."""

    destination_port: Optional[str] = None
    freight_method: Optional[str] = None
    price: Optional[float] = None
    currency: str = "$"
    etd: Optional[str] = None
    eta: Optional[str] = None
    estimated_delivery: Optional[str] = None


class ShippingBlock(BaseModel):
    """Represents a shipping block in the scraped data."""

    destination_country: Optional[str] = None
    options: List[ShippingInfo] = Field(default_factory=list)


class SimilarItem(BaseModel):
    """Represents a similar item in the scraped data."""

    ref_no: Optional[str] = None
    url: Optional[str] = None
    name: Optional[str] = None
    image: Optional[str] = None
    condition: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    currency: str = "$"
    discount_label: Optional[str] = None
    tag: Optional[str] = None


class Review(BaseModel):
    """Represents a review in the scraped data."""

    review_id: Optional[str] = None
    rating: Optional[int] = None
    reviewer_name: Optional[str] = None
    reviewer_country: Optional[str] = None
    date: Optional[str] = None
    verified_buyer: bool = False
    text: Optional[str] = None


class ReviewBlock(BaseModel):
    """Represents a block of reviews in the scraped data."""

    total_reviews_text: Optional[str] = None
    total_reviews_count: Optional[int] = None
    average_rating: Optional[int] = None
    reviews_scraped: int = 0
    reviews: List[Review] = Field(default_factory=list)


class PartListing(BaseModel):
    """Represents a part listing in the scraped data."""

    url: str
    scraped_at: datetime
    ref_no: Optional[str] = None
    item_location: Optional[str] = None
    price: PriceBlock = Field(default_factory=PriceBlock)
    people_viewing_now: Optional[int] = None
    specifications: dict[str, Optional[str]] = Field(default_factory=dict)
    description: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    shipping: ShippingBlock = Field(default_factory=ShippingBlock)
    similar_items: List[SimilarItem] = Field(default_factory=list)
    reviews: Optional[ReviewBlock] = None

    @field_validator("specifications", mode="before")
    @classmethod
    def _drop_dash_placeholders(cls, v: Any) -> Any:
        """Normalise BE FORWARD placeholder dashes to None."""
        if not isinstance(v, dict):
            return v
        return {k: (None if val == "-" else val) for k, val in v.items()}

    def source_key(self) -> str:
        """Deterministic unique key for idempotent bronze inserts."""

        payload = f"{self.ref_no or ''}|{self.url}|{self.scraped_at.isoformat()}"
        return sha256(payload.encode("utf-8")).hexdigest()

    def to_raw_json(self) -> str:
        """Return a JSON string representation of the listing for storage in bronze."""
        return json.dumps(self.model_dump(mode="json"), ensure_ascii=False)
