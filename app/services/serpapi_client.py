from typing import Any
import os
import httpx


class SerpApiClient:
    """Client for SerpAPI Google Flights and search services."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEY not provided or found in environment")
        self.base_url = "https://serpapi.com/search"

    async def search_flights(
        self,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        return_date: str | None = None,
        currency: str = "USD",
        hl: str = "en",
        gl: str = "us",
        adults: int = 1,
        children: int = 0,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        travel_class: int = 1,
        trip_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Search for flights using Google Flights via SerpAPI.

        Args:
            departure_id: Airport code (e.g., "JFK", "LAX") or location
            arrival_id: Airport code (e.g., "LHR", "CDG") or location
            outbound_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (for round trips)
            currency: Currency code (default: USD)
            hl: Language code (default: en)
            gl: Country code (default: us)
            adults: Number of adult passengers
            children: Number of child passengers
            infants_in_seat: Number of infants in seat
            infants_on_lap: Number of infants on lap
            travel_class: Travel class (1=Economy, 2=Premium Economy, 3=Business, 4=First)
            trip_type: Override trip type (1=Round trip, 2=One way)

        Returns:
            Flight search results from SerpAPI
        """
        params = {
            "engine": "google_flights",
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "currency": currency,
            "hl": hl,
            "gl": gl,
            "adults": adults,
            "children": children,
            "infants_in_seat": infants_in_seat,
            "infants_on_lap": infants_on_lap,
            "travel_class": travel_class,
            "api_key": self.api_key,
        }

        # Add return_date if provided (round trip)
        if return_date:
            params["return_date"] = return_date
            params["type"] = 1  # Round trip
        else:
            params["type"] = 2  # One-way

        # Override trip type if explicitly specified
        if trip_type:
            params["type"] = trip_type

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()

    async def search_airports(
        self, query: str, gl: str = "us", hl: str = "en"
    ) -> dict[str, Any]:
        """
        Search for airports/locations to get the correct airport codes.

        Args:
            query: Search query (e.g., "New York", "London", "JFK")
            gl: Country code (default: us)
            hl: Language code (default: en)

        Returns:
            Airport search results
        """
        params = {
            "engine": "google_flights",
            "q": query,
            "gl": gl,
            "hl": hl,
            "api_key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
