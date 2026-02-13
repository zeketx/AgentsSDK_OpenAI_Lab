import csv
import tempfile
import unittest
from pathlib import Path

from app.leadgen.export.sheets import (
    GOOGLE_MAPS_COLUMNS,
    build_google_maps_rows,
    export_google_maps_records_to_csv,
    normalize_google_maps_record,
)


SAMPLE_RECORD = {
    "source": "google_maps",
    "vendor_name": "Sunrise Coffee",
    "contract_category": "Coffee shop",
    "city": "Nashville",
    "state": "TN",
    "source_url": "https://www.google.com/maps",
    "raw_data": {
        "query": "coffee shops",
        "location": "Nashville, Tennessee",
        "address": "123 Main St, Nashville, TN 37203",
        "phone": "+1 615-555-0100",
        "website": "https://sunrisecoffee.example",
        "rating": 4.6,
        "reviews": 215,
        "type": "Coffee shop",
        "place_id": "place_1",
        "data_id": "data_1",
        "data_cid": "cid_1",
        "gps_coordinates": {"latitude": 36.1627, "longitude": -86.7816},
    },
}


class TestGoogleMapsExport(unittest.TestCase):
    def test_normalize_record(self) -> None:
        row = normalize_google_maps_record(SAMPLE_RECORD, fetched_at_utc="2026-02-13T00:00:00Z")
        self.assertEqual(row["vendor_name"], "Sunrise Coffee")
        self.assertEqual(row["category"], "Coffee shop")
        self.assertEqual(row["place_id"], "place_1")
        self.assertEqual(row["latitude"], 36.1627)
        self.assertEqual(row["fetched_at_utc"], "2026-02-13T00:00:00Z")

    def test_build_rows_has_header(self) -> None:
        rows = build_google_maps_rows([SAMPLE_RECORD], fetched_at_utc="2026-02-13T00:00:00Z")
        self.assertEqual(rows[0], GOOGLE_MAPS_COLUMNS)
        self.assertEqual(rows[1][1], "Sunrise Coffee")

    def test_export_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_google_maps_records_to_csv(
                [SAMPLE_RECORD],
                output_dir=tmpdir,
                filename="test_leads.csv",
                fetched_at_utc="2026-02-13T00:00:00Z",
            )
            csv_path = Path(path)
            self.assertTrue(csv_path.exists())

            with csv_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["vendor_name"], "Sunrise Coffee")
            self.assertEqual(rows[0]["query"], "coffee shops")


if __name__ == "__main__":
    unittest.main()

