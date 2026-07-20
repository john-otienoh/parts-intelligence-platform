"""Listing endpoints: paginated catalog + detail view."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.listing import (
    ListingDetail,
    ListingSummary,
    PaginatedListings,
    PriceOut,
    ShippingOptionOut,
    SimilarItemOut,
    ReviewOut,
)

router = APIRouter()


def _build_list_query(
    make: Optional[str],
    model: Optional[str],
    condition: Optional[str],
    min_price: Optional[float],
    max_price: Optional[float],
    category: Optional[str],
    subcategory: Optional[str],
    sort: str,
) -> tuple[str, dict]:
    """Build the WHERE clause and parameters for the list query."""
    where_parts = ["1=1"]
    params: dict = {}

    if make:
        where_parts.append("p.make ILIKE :make")
        params["make"] = f"%{make}%"
    if model:
        where_parts.append("p.model ILIKE :model")
        params["model"] = f"%{model}%"
    if condition:
        where_parts.append("p.condition ILIKE :condition")
        params["condition"] = f"%{condition}%"
    if category:
        where_parts.append("p.title ILIKE :category")
        params["category"] = f"%{category}%"
    if subcategory:
        where_parts.append("p.title ILIKE :subcategory")
        params["subcategory"] = f"%{subcategory}%"
    if min_price is not None:
        where_parts.append("pr.current_price >= :min_price")
        params["min_price"] = min_price
    if max_price is not None:
        where_parts.append("pr.current_price <= :max_price")
        params["max_price"] = max_price

    order_by = {
        "price_asc": "pr.current_price ASC NULLS LAST",
        "price_desc": "pr.current_price DESC NULLS LAST",
        "newest": "p.scraped_at DESC",
        "oldest": "p.scraped_at ASC",
        "views": "p.people_viewing DESC NULLS LAST",
    }.get(sort, "p.scraped_at DESC")

    where_clause = " AND ".join(where_parts)
    return where_clause, params, order_by


@router.get("/", response_model=PaginatedListings)
def list_parts(
    make: Optional[str] = Query(None, description="Filter by make, e.g. TOYOTA"),
    model: Optional[str] = Query(None, description="Filter by model, e.g. Pixisapace"),
    condition: Optional[str] = Query(None, description="New or Used"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("newest", description="price_asc | price_desc | newest | oldest | views"),
    db: Session = Depends(get_db),
):
    """Paginated catalog with faceted filtering.

    Returns lightweight summaries (one image + price per listing).
    """
    where_clause, params, order_by = _build_list_query(
        make, model, condition, min_price, max_price, category, subcategory, sort
    )

    # Count total matching rows
    count_sql = text(f"""
        SELECT COUNT(*) FROM silver.parts p
        LEFT JOIN silver.prices pr USING (ref_no, scraped_at)
        WHERE {where_clause}
    """)
    total = db.execute(count_sql, params).scalar() or 0

    # Fetch paginated results
    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset

    list_sql = text(f"""
        SELECT
            p.ref_no,
            p.title,
            p.make,
            p.model,
            p.condition,
            p.product_name,
            p.model_code,
            p.reg_year_month,
            p.mileage,
            p.engine_model,
            p.engine_size,
            p.fuel,
            p.drive,
            p.people_viewing,
            p.scraped_at,
            pr.currency,
            pr.original_price,
            pr.current_price,
            pr.you_save_amount,
            pr.you_save_percent,
            pr.is_bargain,
            (SELECT image_url FROM silver.images i
             WHERE i.ref_no = p.ref_no AND i.scraped_at = p.scraped_at
             ORDER BY i.id LIMIT 1) AS image
        FROM silver.parts p
        LEFT JOIN silver.prices pr USING (ref_no, scraped_at)
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT :limit OFFSET :offset
    """)

    rows = db.execute(list_sql, params).mappings().all()

    items: List[ListingSummary] = []
    for row in rows:
        items.append(ListingSummary(
            ref_no=row["ref_no"],
            title=row["title"],
            make=row["make"],
            model=row["model"],
            condition=row["condition"],
            product_name=row["product_name"],
            model_code=row["model_code"],
            reg_year_month=row["reg_year_month"],
            mileage=row["mileage"],
            engine_model=row["engine_model"],
            engine_size=row["engine_size"],
            fuel=row["fuel"],
            drive=row["drive"],
            image=row["image"],
            people_viewing=row["people_viewing"],
            scraped_at=row["scraped_at"],
            price=PriceOut(
                currency=row["currency"] or "$",
                original_price=float(row["original_price"]) if row["original_price"] is not None else None,
                current_price=float(row["current_price"]) if row["current_price"] is not None else None,
                you_save_amount=float(row["you_save_amount"]) if row["you_save_amount"] is not None else None,
                you_save_percent=row["you_save_percent"],
                is_bargain_price=row["is_bargain"] or False,
            ) if row["current_price"] is not None else None,
        ))

    return PaginatedListings(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit if limit else 0,
    )


@router.get("/{ref_no}", response_model=ListingDetail)
def get_part(ref_no: str, db: Session = Depends(get_db)):
    """Full detail view for a single listing.

    Includes price, shipping options, images, similar items, and reviews.
    """
    # Fetch the core part + price row
    part_sql = text("""
        SELECT
            p.ref_no, p.url, p.title, p.make, p.model, p.condition,
            p.product_name, p.model_code, p.reg_year_month, p.mileage,
            p.engine_model, p.engine_size, p.fuel, p.drive, p.transmission,
            p.genuine_parts_no, p.description, p.people_viewing, p.scraped_at,
            pr.currency, pr.original_price, pr.current_price,
            pr.you_save_amount, pr.you_save_percent, pr.is_bargain
        FROM silver.parts p
        LEFT JOIN silver.prices pr USING (ref_no, scraped_at)
        WHERE p.ref_no = :ref_no
        ORDER BY p.scraped_at DESC
        LIMIT 1
    """)
    row = db.execute(part_sql, {"ref_no": ref_no}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Listing {ref_no} not found")

    # Fetch related data in parallel (same session, cheap queries)
    images_sql = text("""
        SELECT image_url FROM silver.images
        WHERE ref_no = :ref_no ORDER BY id
    """)
    images = [r[0] for r in db.execute(images_sql, {"ref_no": ref_no}).fetchall()]

    shipping_sql = text("""
        SELECT destination_port, freight_method, price, currency,
               etd, eta, estimated_delivery
        FROM silver.shipping_options
        WHERE ref_no = :ref_no
        ORDER BY price ASC NULLS LAST
    """)
    shipping_rows = db.execute(shipping_sql, {"ref_no": ref_no}).mappings().all()
    shipping_options = [
        ShippingOptionOut(
            destination_port=r["destination_port"],
            freight_method=r["freight_method"],
            price=float(r["price"]) if r["price"] is not None else None,
            currency=r["currency"] or "$",
            etd=r["etd"],
            eta=r["eta"],
            estimated_delivery=r["estimated_delivery"],
        )
        for r in shipping_rows
    ]

    similar_sql = text("""
        SELECT similar_ref_no, name, url, image, condition, price,
               original_price, currency, discount_label, tag
        FROM silver.similar_items
        WHERE listing_ref_no = :ref_no
        ORDER BY price ASC NULLS LAST
    """)
    similar_rows = db.execute(similar_sql, {"ref_no": ref_no}).mappings().all()
    similar_items = [
        SimilarItemOut(
            ref_no=r["similar_ref_no"],
            name=r["name"],
            url=r["url"],
            image=r["image"],
            condition=r["condition"],
            price=float(r["price"]) if r["price"] is not None else None,
            original_price=float(r["original_price"]) if r["original_price"] is not None else None,
            currency=r["currency"] or "$",
            discount_label=r["discount_label"],
            tag=r["tag"],
        )
        for r in similar_rows
    ]

    reviews_sql = text("""
        SELECT review_id, rating, reviewer_name, reviewer_country,
               date, verified_buyer, review_text
        FROM silver.reviews
        WHERE ref_no = :ref_no
        ORDER BY date DESC NULLS LAST
    """)
    review_rows = db.execute(reviews_sql, {"ref_no": ref_no}).mappings().all()
    reviews = [
        ReviewOut(
            review_id=r["review_id"],
            rating=r["rating"],
            reviewer_name=r["reviewer_name"],
            reviewer_country=r["reviewer_country"],
            date=r["date"],
            verified_buyer=r["verified_buyer"] or False,
            text=r["review_text"],
        )
        for r in review_rows
    ]

    return ListingDetail(
        ref_no=row["ref_no"],
        url=row["url"],
        title=row["title"],
        make=row["make"],
        model=row["model"],
        condition=row["condition"],
        product_name=row["product_name"],
        model_code=row["model_code"],
        reg_year_month=row["reg_year_month"],
        mileage=row["mileage"],
        engine_model=row["engine_model"],
        engine_size=row["engine_size"],
        fuel=row["fuel"],
        drive=row["drive"],
        transmission=row["transmission"],
        genuine_parts_no=row["genuine_parts_no"],
        description=row["description"],
        people_viewing=row["people_viewing"],
        scraped_at=row["scraped_at"],
        image=images[0] if images else None,
        price=PriceOut(
            currency=row["currency"] or "$",
            original_price=float(row["original_price"]) if row["original_price"] is not None else None,
            current_price=float(row["current_price"]) if row["current_price"] is not None else None,
            you_save_amount=float(row["you_save_amount"]) if row["you_save_amount"] is not None else None,
            you_save_percent=row["you_save_percent"],
            is_bargain_price=row["is_bargain"] or False,
        ) if row["current_price"] is not None else None,
        images=images,
        shipping_options=shipping_options,
        similar_items=similar_items,
        reviews=reviews,
    )