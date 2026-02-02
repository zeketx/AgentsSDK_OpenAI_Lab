"""Database configuration and models for business listings."""

import hashlib
import json
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Float,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

Base = declarative_base()


class Listing(Base):
    """Master table for business listings from BizBuySell."""

    __tablename__ = "listings"

    id = Column(Integer, primary_key=True)
    external_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    business_category = Column(String(200), nullable=True)
    asking_price = Column(Integer, nullable=True)
    asking_price_raw = Column(String(100), nullable=True)
    location_city = Column(String(200), nullable=True)
    location_state = Column(String(50), nullable=True)
    location_raw = Column(String(300), nullable=True)
    revenue = Column(String(100), nullable=True)
    cash_flow = Column(String(100), nullable=True)
    seller_reason_raw = Column(Text, nullable=True)
    url = Column(String(1000), nullable=False)
    content_hash = Column(String(64), nullable=False)

    # Timestamps
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_retirement_listing = Column(Boolean, default=False, nullable=False)

    # Relationships
    details = relationship("ListingDetail", back_populates="listing", uselist=False)
    snapshots = relationship("ListingSnapshot", back_populates="listing")
    user_actions = relationship("UserAction", back_populates="listing")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_listings_price", "asking_price"),
        Index("idx_listings_location", "location_state", "location_city"),
        Index("idx_listings_retirement", "is_retirement_listing", "is_active"),
        Index("idx_listings_updated", "last_updated_at"),
    )


class ListingDetail(Base):
    """Detailed information scraped from individual listing pages."""

    __tablename__ = "listing_details"

    id = Column(Integer, primary_key=True)
    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Full details
    full_description = Column(Text, nullable=True)
    financial_details = Column(JSON, nullable=True)
    years_in_business = Column(String(50), nullable=True)
    employees = Column(String(50), nullable=True)
    real_estate_included = Column(Boolean, nullable=True)
    inventory_value = Column(String(100), nullable=True)
    training_included = Column(Boolean, nullable=True)
    detailed_location = Column(String(500), nullable=True)
    reason_for_selling = Column(Text, nullable=True)

    # Metadata
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    scrape_status = Column(String(50), default="pending")  # pending, completed, failed

    # Relationship
    listing = relationship("Listing", back_populates="details")


class ListingSnapshot(Base):
    """Historical snapshots for tracking changes."""

    __tablename__ = "listing_snapshots"

    id = Column(Integer, primary_key=True)
    listing_id = Column(
        Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    data_json = Column(JSON, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    listing = relationship("Listing", back_populates="snapshots")

    __table_args__ = (Index("idx_snapshots_listing_date", "listing_id", "created_at"),)


class UserAction(Base):
    """User actions on listings (viewed, interested, ignored)."""

    __tablename__ = "user_actions"

    id = Column(Integer, primary_key=True)
    listing_id = Column(
        Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    action = Column(String(50), nullable=False)  # viewed, interested, ignored
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    listing = relationship("Listing", back_populates="user_actions")

    __table_args__ = (Index("idx_user_actions_listing", "listing_id", "created_at"),)


class ScrapeRun(Base):
    """Log of scraping executions."""

    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True)
    run_type = Column(String(50), nullable=False)  # search, details
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Stats
    listings_found = Column(Integer, default=0)
    new_listings = Column(Integer, default=0)
    updated_listings = Column(Integer, default=0)
    detail_pages_scraped = Column(Integer, default=0)
    errors = Column(Integer, default=0)

    status = Column(String(50), default="running")  # running, completed, failed
    error_message = Column(Text, nullable=True)

    __table_args__ = (Index("idx_scrape_runs_date", "started_at"),)


class ScrapingQueue(Base):
    """Queue for detail page scraping."""

    __tablename__ = "scraping_queue"

    id = Column(Integer, primary_key=True)
    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    priority = Column(Integer, default=0)  # Higher = more priority
    status = Column(
        String(50), default="pending"
    )  # pending, processing, completed, failed
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)


# Database engine setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bizbuysell_listings.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def compute_content_hash(data: dict) -> str:
    """Compute hash for change detection."""
    # Normalize data for consistent hashing
    normalized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
