"""Database operations for BizBuySell listings."""

from datetime import datetime
from typing import Optional, List, Dict, Any, cast

from sqlalchemy.orm import Session

from app.database import (
    Listing,
    ListingDetail,
    ListingSnapshot,
    ScrapingQueue,
    ScrapeRun,
    UserAction,
    compute_content_hash,
)


def get_listing_by_external_id(db: Session, external_id: str) -> Optional[Listing]:
    return db.query(Listing).filter(Listing.external_id == external_id).first()


def save_or_update_listing(
    db: Session, listing_data: Dict
) -> tuple[Listing, bool, bool]:
    """
    Save new listing or update existing if changes detected.
    Returns (listing, is_new, is_updated).
    """
    external_id = listing_data.get("external_id")
    if not external_id:
        raise ValueError("external_id is required")

    content_hash = compute_content_hash(listing_data)
    existing = get_listing_by_external_id(db, external_id)
    if not existing:
        listing = Listing(
            external_id=external_id,
            title=listing_data.get("title", ""),
            business_category=listing_data.get("business_category"),
            asking_price=listing_data.get("asking_price"),
            asking_price_raw=listing_data.get("asking_price_raw"),
            location_city=listing_data.get("location_city"),
            location_state=listing_data.get("location_state"),
            location_raw=listing_data.get("location_raw"),
            revenue=listing_data.get("revenue"),
            cash_flow=listing_data.get("cash_flow"),
            seller_reason_raw=listing_data.get("seller_reason_raw"),
            url=listing_data.get("url"),
            content_hash=content_hash,
            is_retirement_listing=listing_data.get("is_retirement_listing", False),
        )
        db.add(listing)
        db.flush()

        snapshot = ListingSnapshot(
            listing_id=listing.id,
            data_json=listing_data,
            content_hash=content_hash,
        )
        db.add(snapshot)
        return listing, True, False

    if str(existing.content_hash) != content_hash:
        existing_any = cast(Any, existing)
        existing_any.title = listing_data.get("title", existing_any.title)
        existing_any.business_category = listing_data.get(
            "business_category", existing_any.business_category
        )
        existing_any.asking_price = listing_data.get(
            "asking_price", existing_any.asking_price
        )
        existing_any.asking_price_raw = listing_data.get(
            "asking_price_raw", existing_any.asking_price_raw
        )
        existing_any.location_city = listing_data.get(
            "location_city", existing_any.location_city
        )
        existing_any.location_state = listing_data.get(
            "location_state", existing_any.location_state
        )
        existing_any.location_raw = listing_data.get(
            "location_raw", existing_any.location_raw
        )
        existing_any.revenue = listing_data.get("revenue", existing_any.revenue)
        existing_any.cash_flow = listing_data.get("cash_flow", existing_any.cash_flow)
        existing_any.seller_reason_raw = listing_data.get(
            "seller_reason_raw", existing_any.seller_reason_raw
        )
        existing_any.url = listing_data.get("url", existing_any.url)
        existing_any.is_retirement_listing = listing_data.get(
            "is_retirement_listing", existing_any.is_retirement_listing
        )
        existing_any.content_hash = content_hash  # type: ignore[assignment]
        existing_any.last_updated_at = datetime.utcnow()  # type: ignore[assignment]

        snapshot = ListingSnapshot(
            listing_id=existing.id,
            data_json=listing_data,
            content_hash=content_hash,
        )
        db.add(snapshot)
        return existing, False, True

    existing_any = cast(Any, existing)
    existing_any.last_updated_at = datetime.utcnow()  # type: ignore[assignment]
    return existing, False, False


def queue_listing_for_details(db: Session, listing_id: int, priority: int = 0) -> None:
    existing = (
        db.query(ScrapingQueue).filter(ScrapingQueue.listing_id == listing_id).first()
    )
    if existing:
        existing_any = cast(Any, existing)
        if existing_any.status in {"failed", "completed"}:
            existing_any.status = "pending"  # type: ignore[assignment]
        if priority > existing_any.priority:
            existing_any.priority = priority  # type: ignore[assignment]
        return

    db.add(
        ScrapingQueue(
            listing_id=listing_id,
            priority=priority,
            status="pending",
        )
    )


def get_pending_detail_scrapes(db: Session, limit: int = 50) -> List[ScrapingQueue]:
    return (
        db.query(ScrapingQueue)
        .filter(ScrapingQueue.status == "pending")
        .order_by(ScrapingQueue.priority.desc(), ScrapingQueue.created_at.asc())
        .limit(limit)
        .all()
    )


def get_listing_by_id(db: Session, listing_id: int) -> Optional[Listing]:
    return db.query(Listing).filter(Listing.id == listing_id).first()


def save_listing_detail(
    db: Session, listing_id: int, detail_data: Dict
) -> ListingDetail:
    existing = (
        db.query(ListingDetail).filter(ListingDetail.listing_id == listing_id).first()
    )
    if existing:
        existing_any = cast(Any, existing)
        for key, value in detail_data.items():
            if hasattr(existing_any, key):
                setattr(existing_any, key, value)
        existing_any.scrape_status = "completed"  # type: ignore[assignment]
        existing_any.scraped_at = datetime.utcnow()  # type: ignore[assignment]
        db.flush()
        return existing

    detail = ListingDetail(
        listing_id=listing_id,
        scrape_status="completed",
        scraped_at=datetime.utcnow(),
        **detail_data,
    )
    db.add(detail)
    db.flush()
    return detail


def mark_queue_processing(db: Session, queue_item: ScrapingQueue) -> None:
    queue_any = cast(Any, queue_item)
    queue_any.status = "processing"  # type: ignore[assignment]
    db.flush()


def mark_queue_completed(db: Session, queue_item: ScrapingQueue) -> None:
    queue_any = cast(Any, queue_item)
    queue_any.status = "completed"  # type: ignore[assignment]
    queue_any.processed_at = datetime.utcnow()  # type: ignore[assignment]
    db.flush()


def mark_queue_failed(db: Session, queue_item: ScrapingQueue, error: str) -> None:
    queue_any = cast(Any, queue_item)
    queue_any.status = "failed"  # type: ignore[assignment]
    queue_any.retry_count = int(queue_any.retry_count or 0) + 1  # type: ignore[assignment]
    queue_any.error_message = error  # type: ignore[assignment]
    queue_any.processed_at = datetime.utcnow()  # type: ignore[assignment]
    db.flush()


def create_scrape_run(db: Session, run_type: str) -> ScrapeRun:
    run = ScrapeRun(run_type=run_type)
    db.add(run)
    db.flush()
    return run


def update_scrape_run(db: Session, run_id: int, stats: Dict) -> None:
    run = db.query(ScrapeRun).filter(ScrapeRun.id == run_id).first()
    if not run:
        return

    for key, value in stats.items():
        if hasattr(run, key):
            setattr(run, key, value)
    db.flush()


def get_new_listings(db: Session, since_date: datetime) -> List[Listing]:
    return db.query(Listing).filter(Listing.first_seen_at >= since_date).all()


def get_retirement_listings(
    db: Session,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
) -> List[Listing]:
    query = db.query(Listing).filter(Listing.is_retirement_listing.is_(True))
    if min_price is not None:
        query = query.filter(Listing.asking_price >= min_price)
    if max_price is not None:
        query = query.filter(Listing.asking_price <= max_price)
    if state:
        query = query.filter(Listing.location_state == state)
    if city:
        query = query.filter(Listing.location_city == city)
    return query.order_by(Listing.last_updated_at.desc()).all()


def mark_listing_inactive(db: Session, external_id: str) -> None:
    listing = get_listing_by_external_id(db, external_id)
    if listing:
        listing_any = cast(Any, listing)
        listing_any.is_active = False  # type: ignore[assignment]
        listing_any.last_updated_at = datetime.utcnow()  # type: ignore[assignment]


def record_user_action(
    db: Session, listing_id: int, action: str, notes: Optional[str] = None
) -> UserAction:
    user_action = UserAction(listing_id=listing_id, action=action, notes=notes)
    db.add(user_action)
    db.flush()
    return user_action
