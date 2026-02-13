"""CSV and Google Sheets export for Google Maps lead records."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GOOGLE_MAPS_COLUMNS = [
    "source",
    "vendor_name",
    "category",
    "address",
    "city",
    "state",
    "phone",
    "website",
    "rating",
    "reviews",
    "place_id",
    "data_id",
    "data_cid",
    "latitude",
    "longitude",
    "source_url",
    "query",
    "location",
    "fetched_at_utc",
]


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_google_maps_record(
    record: dict[str, Any], fetched_at_utc: str | None = None
) -> dict[str, Any]:
    raw = record.get("raw_data", {}) if isinstance(record.get("raw_data"), dict) else {}
    gps = (
        raw.get("gps_coordinates", {})
        if isinstance(raw.get("gps_coordinates"), dict)
        else {}
    )
    ts = fetched_at_utc or datetime.now(timezone.utc).isoformat()
    return {
        "source": record.get("source", "google_maps"),
        "vendor_name": record.get("vendor_name") or "",
        "category": record.get("contract_category") or raw.get("type") or "",
        "address": raw.get("address") or "",
        "city": record.get("city") or "",
        "state": record.get("state") or "TN",
        "phone": raw.get("phone") or "",
        "website": raw.get("website") or "",
        "rating": _safe_float(raw.get("rating")),
        "reviews": raw.get("reviews") or "",
        "place_id": raw.get("place_id") or "",
        "data_id": raw.get("data_id") or "",
        "data_cid": raw.get("data_cid") or "",
        "latitude": _safe_float(gps.get("latitude")),
        "longitude": _safe_float(gps.get("longitude")),
        "source_url": record.get("source_url") or "",
        "query": raw.get("query") or "",
        "location": raw.get("location") or "",
        "fetched_at_utc": ts,
    }


def build_google_maps_rows(
    records: list[dict[str, Any]], fetched_at_utc: str | None = None
) -> list[list[Any]]:
    rows: list[list[Any]] = [GOOGLE_MAPS_COLUMNS]
    for record in records:
        normalized = normalize_google_maps_record(record, fetched_at_utc=fetched_at_utc)
        rows.append([normalized.get(col, "") for col in GOOGLE_MAPS_COLUMNS])
    return rows


def export_google_maps_records_to_csv(
    records: list[dict[str, Any]],
    output_dir: str = "data/leadgen",
    filename: str = "google_maps_leads.csv",
    fetched_at_utc: str | None = None,
) -> str:
    output_path = Path(output_dir) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=GOOGLE_MAPS_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(
                normalize_google_maps_record(record, fetched_at_utc=fetched_at_utc)
            )
    return str(output_path)


def export_google_maps_records_to_sheet(
    records: list[dict[str, Any]],
    spreadsheet_id: str,
    credentials_path: str,
    worksheet_name: str = "Google Maps Leads",
    clear_first: bool = True,
    fetched_at_utc: str | None = None,
) -> str:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    if not credentials_path:
        raise ValueError("credentials_path is required")

    import gspread  # Imported lazily so local tests don't require live auth

    client = gspread.service_account(filename=credentials_path)
    spreadsheet = client.open_by_key(spreadsheet_id)

    rows = build_google_maps_rows(records, fetched_at_utc=fetched_at_utc)
    required_rows = max(1000, len(rows) + 10)
    required_cols = max(26, len(GOOGLE_MAPS_COLUMNS) + 2)

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=str(required_rows),
            cols=str(required_cols),
        )

    if clear_first:
        worksheet.clear()

    worksheet.update("A1", rows)
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

