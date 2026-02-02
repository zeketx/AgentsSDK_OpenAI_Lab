"""FastAPI endpoints for BizBuySell listings."""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import Listing, ListingDetail, ScrapeRun, get_db
from app.services import listing_service
from app.services.export_service import export_listings_to_csv


router = APIRouter()


class ListingResponse(BaseModel):
    id: int
    external_id: str
    title: str
    business_category: Optional[str]
    asking_price: Optional[int]
    asking_price_raw: Optional[str]
    location_city: Optional[str]
    location_state: Optional[str]
    location_raw: Optional[str]
    revenue: Optional[str]
    cash_flow: Optional[str]
    seller_reason_raw: Optional[str]
    url: str
    is_active: bool
    is_retirement_listing: bool
    first_seen_at: datetime
    last_updated_at: datetime

    class Config:
        orm_mode = True


class ListingDetailResponse(BaseModel):
    full_description: Optional[str]
    financial_details: Optional[dict]
    years_in_business: Optional[str]
    employees: Optional[str]
    real_estate_included: Optional[bool]
    inventory_value: Optional[str]
    training_included: Optional[bool]
    detailed_location: Optional[str]
    reason_for_selling: Optional[str]
    scraped_at: datetime
    scrape_status: str

    class Config:
        orm_mode = True


class ListingWithDetailsResponse(ListingResponse):
    details: Optional[ListingDetailResponse]


class ListingActionRequest(BaseModel):
    action: str
    notes: Optional[str] = None


class ScrapeRunResponse(BaseModel):
    id: int
    run_type: str
    started_at: datetime
    completed_at: Optional[datetime]
    listings_found: int
    new_listings: int
    updated_listings: int
    detail_pages_scraped: int
    errors: int
    status: str
    error_message: Optional[str]

    class Config:
        orm_mode = True


class StatsResponse(BaseModel):
    total_listings: int
    active_listings: int
    retirement_listings: int
    new_today: int


class ExportResponse(BaseModel):
    path: str


@router.get("/listings", response_model=List[ListingResponse])
def list_listings(
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    is_retirement: Optional[bool] = None,
    is_active: Optional[bool] = True,
    db: Session = Depends(get_db),
):
    query = db.query(Listing)
    if is_active is not None:
        query = query.filter(Listing.is_active.is_(is_active))
    if is_retirement is not None:
        query = query.filter(Listing.is_retirement_listing.is_(is_retirement))
    if min_price is not None:
        query = query.filter(Listing.asking_price >= min_price)
    if max_price is not None:
        query = query.filter(Listing.asking_price <= max_price)
    if state:
        query = query.filter(Listing.location_state == state)
    if city:
        query = query.filter(Listing.location_city == city)
    return query.order_by(Listing.last_updated_at.desc()).all()


@router.get("/listings/new", response_model=List[ListingResponse])
def list_new_listings(since_hours: int = 24, db: Session = Depends(get_db)):
    since_date = datetime.utcnow() - timedelta(hours=since_hours)
    return listing_service.get_new_listings(db, since_date)


@router.get("/listings/{listing_id}", response_model=ListingWithDetailsResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.post("/listings/{listing_id}/action")
def mark_listing_action(
    listing_id: int, action: ListingActionRequest, db: Session = Depends(get_db)
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing_service.record_user_action(db, listing_id, action.action, action.notes)
    db.commit()
    return {"status": "ok"}


@router.get("/scrape-runs", response_model=List[ScrapeRunResponse])
def list_scrape_runs(db: Session = Depends(get_db)):
    return db.query(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(50).all()


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Listing).count()
    active = db.query(Listing).filter(Listing.is_active.is_(True)).count()
    retirement = (
        db.query(Listing).filter(Listing.is_retirement_listing.is_(True)).count()
    )
    since = datetime.utcnow() - timedelta(days=1)
    new_today = db.query(Listing).filter(Listing.first_seen_at >= since).count()
    return StatsResponse(
        total_listings=total,
        active_listings=active,
        retirement_listings=retirement,
        new_today=new_today,
    )


@router.get("/export", response_model=ExportResponse)
def export_listings(
    only_retirement: bool = False,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    output_path = "bizbuysell_export.csv"
    path = export_listings_to_csv(
        db,
        output_path=output_path,
        only_retirement=only_retirement,
        active_only=active_only,
    )
    return ExportResponse(path=path)
