"""Google Maps lead ingest via SerpApi."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from app.leadgen.export.sheets import (
    export_google_maps_records_to_csv,
    export_google_maps_records_to_sheet,
)

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"
DEFAULT_OUTPUT_DIR = "data/leadgen"
PAGE_SIZE = 20

load_dotenv()


class GoogleMapsIngest:
    """Fetch lead candidates from Google Maps search results."""

    def __init__(
        self,
        query: str,
        location: str,
        api_key: str | None = None,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        limit: int = 100,
        hl: str = "en",
        gl: str = "us",
        dedupe_across_runs: bool = True,
        seen_ids_path: str | None = None,
    ) -> None:
        self.query = query.strip()
        self.location = location.strip()
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")
        self.output_dir = output_dir
        self.limit = max(1, limit)
        self.hl = hl
        self.gl = gl
        self.dedupe_across_runs = dedupe_across_runs
        if seen_ids_path:
            self.seen_ids_path = Path(seen_ids_path)
        else:
            self.seen_ids_path = Path(output_dir) / "google_maps_seen_ids.json"

        if not self.query:
            raise ValueError("query is required")
        if not self.location:
            raise ValueError("location is required")
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEY is required")

    def _load_seen_ids(self) -> set[str]:
        if not self.dedupe_across_runs:
            return set()
        if not self.seen_ids_path.exists():
            return set()
        try:
            data = json.loads(self.seen_ids_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return set()
            return {str(item).strip().lower() for item in data if str(item).strip()}
        except Exception:
            return set()

    def _save_seen_ids(self, seen_ids: set[str]) -> None:
        if not self.dedupe_across_runs:
            return
        self.seen_ids_path.parent.mkdir(parents=True, exist_ok=True)
        self.seen_ids_path.write_text(
            json.dumps(sorted(seen_ids), indent=2),
            encoding="utf-8",
        )

    async def _search_page(self, start: int) -> dict[str, Any]:
        params = {
            "engine": "google_maps",
            "type": "search",
            "q": f"{self.query} in {self.location}",
            "hl": self.hl,
            "gl": self.gl,
            "start": start,
            "api_key": self.api_key,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(SERPAPI_SEARCH_URL, params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _extract_city_state(address: str | None) -> tuple[str | None, str]:
        if not address:
            return None, "TN"
        parts = [p.strip() for p in address.split(",") if p.strip()]
        if len(parts) < 2:
            return None, "TN"
        city = parts[-2]
        state = "TN"
        last = parts[-1].upper()
        if " TN" in f" {last}" or last == "TN":
            state = "TN"
        return city, state

    def _map_result_to_record(self, result: dict[str, Any]) -> dict[str, Any] | None:
        title = (result.get("title") or "").strip()
        if not title:
            return None

        address = result.get("address")
        city, state = self._extract_city_state(address)
        data_id = result.get("data_id")
        place_id = result.get("place_id")
        source_url = (
            result.get("place_id_search")
            or result.get("website")
            or "https://www.google.com/maps"
        )
        rating = result.get("rating")
        reviews = result.get("reviews")

        return {
            "source": "google_maps",
            "vendor_name": title,
            "total_payments": None,
            "contract_amount": None,
            "contract_title": None,
            "contract_category": result.get("type"),
            "license_type": None,
            "license_status": None,
            "city": city,
            "state": state,
            "county": None,
            "source_url": source_url,
            "raw_data": {
                "query": self.query,
                "location": self.location,
                "address": address,
                "phone": result.get("phone"),
                "website": result.get("website"),
                "rating": rating,
                "reviews": reviews,
                "type": result.get("type"),
                "place_id": place_id,
                "data_id": data_id,
                "data_cid": result.get("data_cid"),
                "gps_coordinates": result.get("gps_coordinates"),
            },
        }

    def save_intermediate(self, records: list[dict[str, Any]]) -> str:
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        output_path = Path(self.output_dir) / "google_maps_raw.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        return str(output_path)

    async def fetch(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        seen_ids: set[str] = self._load_seen_ids()
        start = 0

        while len(records) < self.limit:
            payload = await self._search_page(start=start)
            rows = payload.get("local_results", [])
            if not rows:
                break

            added = 0
            for row in rows:
                record = self._map_result_to_record(row)
                if not record:
                    continue

                raw = record["raw_data"]
                dedupe_key = (
                    str(raw.get("place_id") or raw.get("data_id") or record["vendor_name"])
                    .strip()
                    .lower()
                )
                if dedupe_key in seen_ids:
                    continue
                seen_ids.add(dedupe_key)
                records.append(record)
                added += 1
                if len(records) >= self.limit:
                    break

            if added == 0:
                break
            start += PAGE_SIZE

        self.save_intermediate(records)
        self._save_seen_ids(seen_ids)
        return records


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Google Maps lead ingest")
    parser.add_argument("--query", required=True, help="Business query, e.g. 'coffee shops'")
    parser.add_argument("--location", required=True, help="Location, e.g. 'Memphis, Tennessee'")
    parser.add_argument("--limit", type=int, default=100, help="Max leads to collect")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument(
        "--no-cross-run-dedupe",
        action="store_true",
        help="Disable dedupe against previously collected place IDs",
    )
    parser.add_argument(
        "--seen-ids-path",
        default=None,
        help="Optional path to persisted dedupe IDs JSON file",
    )
    parser.add_argument(
        "--to-sheets",
        action="store_true",
        help="Export fetched results to Google Sheets",
    )
    parser.add_argument(
        "--worksheet-name",
        default="Google Maps Leads",
        help="Worksheet name for Google Sheets export",
    )
    parser.add_argument(
        "--sheets-spreadsheet-id",
        default=os.getenv("LEADGEN_SHEETS_SPREADSHEET_ID", ""),
        help="Google Sheets spreadsheet ID (or set LEADGEN_SHEETS_SPREADSHEET_ID)",
    )
    parser.add_argument(
        "--sheets-credentials-path",
        default=os.getenv(
            "LEADGEN_SHEETS_CREDENTIALS_PATH",
            "leadgen_service_account.json",
        ),
        help="Service account JSON path (or set LEADGEN_SHEETS_CREDENTIALS_PATH)",
    )
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    ingest = GoogleMapsIngest(
        query=args.query,
        location=args.location,
        limit=args.limit,
        output_dir=args.output_dir,
        dedupe_across_runs=not args.no_cross_run_dedupe,
        seen_ids_path=args.seen_ids_path,
    )
    records = await ingest.fetch()
    print(f"Fetched {len(records)} Google Maps leads")
    print(f"Saved to {Path(args.output_dir) / 'google_maps_raw.json'}")

    csv_path = export_google_maps_records_to_csv(records, output_dir=args.output_dir)
    print(f"Saved CSV to {csv_path}")

    if args.to_sheets:
        sheet_url = export_google_maps_records_to_sheet(
            records=records,
            spreadsheet_id=args.sheets_spreadsheet_id,
            credentials_path=args.sheets_credentials_path,
            worksheet_name=args.worksheet_name,
        )
        print(f"Exported to Google Sheets: {sheet_url}")


if __name__ == "__main__":
    asyncio.run(_main())
