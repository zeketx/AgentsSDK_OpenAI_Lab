import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.leadgen.ingest.google_maps import GoogleMapsIngest


class TestGoogleMapsIngest(unittest.IsolatedAsyncioTestCase):
    async def test_coffee_shops_ingest_saves_deduped_results(self) -> None:
        page_one = {
            "local_results": [
                {
                    "title": "Sunrise Coffee",
                    "address": "123 Main St, Nashville, TN 37203",
                    "website": "https://sunrisecoffee.example",
                    "phone": "+1 615-555-0100",
                    "rating": 4.6,
                    "reviews": 215,
                    "type": "Coffee shop",
                    "place_id": "place_1",
                    "data_id": "data_1",
                    "data_cid": "cid_1",
                    "gps_coordinates": {"latitude": 36.1627, "longitude": -86.7816},
                },
                {
                    "title": "Bean & Brew",
                    "address": "98 River Rd, Nashville, TN 37201",
                    "website": "https://beanbrew.example",
                    "phone": "+1 615-555-0101",
                    "rating": 4.5,
                    "reviews": 180,
                    "type": "Coffee shop",
                    "place_id": "place_2",
                    "data_id": "data_2",
                    "data_cid": "cid_2",
                    "gps_coordinates": {"latitude": 36.1630, "longitude": -86.7820},
                },
            ]
        }
        page_two = {
            "local_results": [
                {
                    "title": "Sunrise Coffee",
                    "address": "123 Main St, Nashville, TN 37203",
                    "website": "https://sunrisecoffee.example",
                    "phone": "+1 615-555-0100",
                    "rating": 4.6,
                    "reviews": 215,
                    "type": "Coffee shop",
                    "place_id": "place_1",  # duplicate
                    "data_id": "data_1",
                },
                {
                    "title": "Roaster Corner",
                    "address": "11 Oak Ave, Nashville, TN 37219",
                    "website": "https://roastercorner.example",
                    "phone": "+1 615-555-0102",
                    "rating": 4.4,
                    "reviews": 89,
                    "type": "Coffee shop",
                    "place_id": "place_3",
                    "data_id": "data_3",
                    "data_cid": "cid_3",
                    "gps_coordinates": {"latitude": 36.1670, "longitude": -86.7900},
                },
            ]
        }
        page_three = {"local_results": []}

        async def fake_search_page(self, start: int):
            if start == 0:
                return page_one
            if start == 20:
                return page_two
            return page_three

        with tempfile.TemporaryDirectory() as tmpdir:
            ingest = GoogleMapsIngest(
                query="coffee shops",
                location="Nashville, Tennessee",
                api_key="test_api_key",
                output_dir=tmpdir,
                limit=5,
            )

            with patch.object(GoogleMapsIngest, "_search_page", new=fake_search_page):
                rows = await ingest.fetch()

            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["vendor_name"], "Sunrise Coffee")
            self.assertEqual(rows[1]["vendor_name"], "Bean & Brew")
            self.assertEqual(rows[2]["vendor_name"], "Roaster Corner")
            self.assertEqual(rows[0]["source"], "google_maps")
            self.assertEqual(rows[0]["raw_data"]["type"], "Coffee shop")

            output_file = Path(tmpdir) / "google_maps_raw.json"
            self.assertTrue(output_file.exists())

            saved = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(len(saved), 3)
            self.assertEqual(saved[0]["city"], "Nashville")

    async def test_cross_run_dedupe_uses_seen_ids_store(self) -> None:
        first_page = {
            "local_results": [
                {
                    "title": "Sunrise Coffee",
                    "address": "123 Main St, Nashville, TN 37203",
                    "type": "Coffee shop",
                    "place_id": "place_1",
                    "data_id": "data_1",
                },
                {
                    "title": "Bean & Brew",
                    "address": "98 River Rd, Nashville, TN 37201",
                    "type": "Coffee shop",
                    "place_id": "place_2",
                    "data_id": "data_2",
                },
            ]
        }
        second_page = {"local_results": []}
        second_run_page = {
            "local_results": [
                {
                    "title": "Sunrise Coffee",
                    "address": "123 Main St, Nashville, TN 37203",
                    "type": "Coffee shop",
                    "place_id": "place_1",
                    "data_id": "data_1",
                },
                {
                    "title": "Roaster Corner",
                    "address": "11 Oak Ave, Nashville, TN 37219",
                    "type": "Coffee shop",
                    "place_id": "place_3",
                    "data_id": "data_3",
                },
            ]
        }

        async def fake_first_run(self, start: int):
            if start == 0:
                return first_page
            return second_page

        async def fake_second_run(self, start: int):
            if start == 0:
                return second_run_page
            return second_page

        with tempfile.TemporaryDirectory() as tmpdir:
            seen_ids_path = str(Path(tmpdir) / "seen_ids.json")
            first = GoogleMapsIngest(
                query="coffee shops",
                location="Nashville, Tennessee",
                api_key="test_api_key",
                output_dir=tmpdir,
                limit=10,
                seen_ids_path=seen_ids_path,
            )
            with patch.object(GoogleMapsIngest, "_search_page", new=fake_first_run):
                rows_first = await first.fetch()
            self.assertEqual(len(rows_first), 2)

            second = GoogleMapsIngest(
                query="coffee shops",
                location="Nashville, Tennessee",
                api_key="test_api_key",
                output_dir=tmpdir,
                limit=10,
                seen_ids_path=seen_ids_path,
            )
            with patch.object(GoogleMapsIngest, "_search_page", new=fake_second_run):
                rows_second = await second.fetch()

            self.assertEqual(len(rows_second), 1)
            self.assertEqual(rows_second[0]["vendor_name"], "Roaster Corner")


if __name__ == "__main__":
    unittest.main()
