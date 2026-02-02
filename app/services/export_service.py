"""Export listings from SQLite to CSV."""

import csv
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database import Listing


def export_listings_to_csv(
    db: Session,
    output_path: str,
    only_retirement: bool = False,
    active_only: bool = True,
) -> str:
    query = db.query(Listing)
    if active_only:
        query = query.filter(Listing.is_active.is_(True))
    if only_retirement:
        query = query.filter(Listing.is_retirement_listing.is_(True))

    rows = query.order_by(Listing.last_updated_at.desc()).all()

    fieldnames = [
        "external_id",
        "title",
        "business_category",
        "asking_price",
        "asking_price_raw",
        "location_city",
        "location_state",
        "location_raw",
        "revenue",
        "cash_flow",
        "seller_reason_raw",
        "url",
        "is_retirement_listing",
        "first_seen_at",
        "last_updated_at",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for listing in rows:
            writer.writerow(
                {
                    "external_id": listing.external_id,
                    "title": listing.title,
                    "business_category": listing.business_category,
                    "asking_price": listing.asking_price,
                    "asking_price_raw": listing.asking_price_raw,
                    "location_city": listing.location_city,
                    "location_state": listing.location_state,
                    "location_raw": listing.location_raw,
                    "revenue": listing.revenue,
                    "cash_flow": listing.cash_flow,
                    "seller_reason_raw": listing.seller_reason_raw,
                    "url": listing.url,
                    "is_retirement_listing": listing.is_retirement_listing,
                    "first_seen_at": listing.first_seen_at,
                    "last_updated_at": listing.last_updated_at,
                }
            )

    return output_path
