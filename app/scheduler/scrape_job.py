"""Scheduler job for BizBuySell daily scraping."""

import asyncio
from datetime import datetime
from typing import List, cast

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import init_db, SessionLocal
from app.parsers.bizbuysell import BizBuySellParser
from app.services import listing_service


TARGET_URL = "https://www.bizbuysell.com/retiring-owner-businesses-for-sale/?q=bGM9SmtjOU16QW1RejFWVXlaVFBWUk9KbFE5TXpVNE9UVS9Ka2M5TXpBbVF6MVZVeVpUUFZSWUpsUTlOVE14Tmo4bVJ6MHpNQ1pEUFZWVEpsTTlWRmdtVkQwMk1EWXlQeVpIUFRNd0prTTlWVk1tVXoxVVRpWlVQVFk0TURNPQ%3D%3D"


async def run_search_scrape() -> None:
    init_db()
    parser = BizBuySellParser()
    db = SessionLocal()
    run = listing_service.create_scrape_run(db, run_type="search")
    db.commit()
    run_id = cast(int, run.id)

    listings_found = 0
    new_listings = 0
    updated_listings = 0
    errors = 0

    try:
        next_url = TARGET_URL
        visited_urls = set()
        while next_url and next_url not in visited_urls:
            visited_urls.add(next_url)
            html = await parser.fetch_page(next_url)
            page_listings = parser.parse_search_results(html)
            listings_found += len(page_listings)

            for listing_data in page_listings:
                try:
                    listing, is_new, is_updated = (
                        listing_service.save_or_update_listing(db, listing_data)
                    )
                    if is_new:
                        new_listings += 1
                        listing_service.queue_listing_for_details(
                            db, listing.id, priority=10
                        )
                    elif is_updated:
                        updated_listings += 1
                        listing_service.queue_listing_for_details(
                            db, listing.id, priority=5
                        )
                except Exception:
                    errors += 1
            db.commit()

            next_url = parser.find_next_page_url(html, next_url)

        listing_service.update_scrape_run(
            db,
            run_id,  # type: ignore[arg-type]
            {
                "listings_found": listings_found,
                "new_listings": new_listings,
                "updated_listings": updated_listings,
                "errors": errors,
                "status": "completed",
                "completed_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        listing_service.update_scrape_run(
            db,
            run_id,  # type: ignore[arg-type]
            {
                "errors": errors + 1,
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.utcnow(),
            },
        )
        db.commit()
    finally:
        db.close()


async def run_detail_scrape(
    batch_size: int = 25, request_timeout: float = 90.0
) -> None:
    init_db()
    parser = BizBuySellParser()
    db = SessionLocal()
    run = listing_service.create_scrape_run(db, run_type="details")
    db.commit()
    run_id = cast(int, run.id)

    detail_pages_scraped = 0
    errors = 0

    try:
        queue_items = listing_service.get_pending_detail_scrapes(db, limit=batch_size)
        for queue_item in queue_items:
            listing_service.mark_queue_processing(db, queue_item)
            db.commit()

            listing = listing_service.get_listing_by_id(
                db,
                cast(int, queue_item.listing_id),
            )
            if not listing:
                listing_service.mark_queue_failed(db, queue_item, "Listing not found")
                db.commit()
                continue

            try:
                print(f"Detail scrape: {listing.external_id} {listing.url}")
                html, _meta = await parser.fetch_page_with_metadata(
                    str(listing.url), timeout=request_timeout
                )
                detail_data = parser.parse_detail_page(html)
                listing_service.save_listing_detail(
                    db,
                    cast(int, listing.id),
                    detail_data,
                )
                listing_service.mark_queue_completed(db, queue_item)
                detail_pages_scraped += 1
                db.commit()
            except Exception as exc:
                errors += 1
                listing_service.mark_queue_failed(db, queue_item, str(exc))
                db.commit()

        listing_service.update_scrape_run(
            db,
            run_id,  # type: ignore[arg-type]
            {
                "detail_pages_scraped": detail_pages_scraped,
                "errors": errors,
                "status": "completed",
                "completed_at": datetime.utcnow(),
            },
        )
        db.commit()
    except Exception as exc:
        listing_service.update_scrape_run(
            db,
            run_id,  # type: ignore[arg-type]
            {
                "errors": errors + 1,
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.utcnow(),
            },
        )
        db.commit()
    finally:
        db.close()


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_search_scrape, "cron", hour=8, minute=0)
    scheduler.add_job(run_detail_scrape, "cron", hour=8, minute=30)
    scheduler.start()
    return scheduler


def run_now():
    asyncio.run(run_search_scrape())
