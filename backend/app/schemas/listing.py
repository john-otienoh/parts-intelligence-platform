"""Pydantic response models for listings endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PriceOut(BaseModel):
    currency: str = "$"
    original_price: Optional[float] = None
    current_price: Optional[float] = None
    you_save_amount: Optional[float] = None
    you_save_percent: Optional[int] = None
    is_bargain_price: bool = False

    class Config:
        from_attributes = True


class ShippingOptionOut(BaseModel):
    destination_port: Optional[str] = None
    freight_method: Optional[str] = None
    price: Optional[float] = None
    currency: str = "$"
    etd: Optional[str] = None
    eta: Optional[str] = None
    estimated_delivery: Optional[str] = None

    class Config:
        from_attributes = True


class SimilarItemOut(BaseModel):
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

    class Config:
        from_attributes = True


class ReviewOut(BaseModel):
    review_id: Optional[str] = None
    rating: Optional[int] = None
    reviewer_name: Optional[str] = None
    reviewer_country: Optional[str] = None
    date: Optional[str] = None
    verified_buyer: bool = False
    text: Optional[str] = None

    class Config:
        from_attributes = True


class ListingSummary(BaseModel):
    """Lightweight response for the list endpoint."""
    ref_no: str
    title: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    condition: Optional[str] = None
    product_name: Optional[str] = None
    model_code: Optional[str] = None
    reg_year_month: Optional[str] = None
    mileage: Optional[str] = None
    engine_model: Optional[str] = None
    engine_size: Optional[str] = None
    fuel: Optional[str] = None
    drive: Optional[str] = None
    image: Optional[str] = None
    price: Optional[PriceOut] = None
    people_viewing: Optional[int] = None
    scraped_at: datetime

    class Config:
        from_attributes = True


class ListingDetail(ListingSummary):
    """Full response for the detail endpoint."""
    url: Optional[str] = None
    description: Optional[str] = None
    genuine_parts_no: Optional[str] = None
    transmission: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    shipping_options: List[ShippingOptionOut] = Field(default_factory=list)
    similar_items: List[SimilarItemOut] = Field(default_factory=list)
    reviews: List[ReviewOut] = Field(default_factory=list)


class PaginatedListings(BaseModel):
    items: List[ListingSummary]
    total: int
    page: int
    limit: int
    pages: int