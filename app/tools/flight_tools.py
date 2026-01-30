"""Flight search tools for the travel agent."""

from typing import Any
from agents import function_tool
from app.services.serpapi_client import SerpApiClient


@function_tool
def search_one_way_flight(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    travel_class: str = "Economy",
    adults: int = 1,
    currency: str = "USD",
) -> dict[str, Any]:
    """
    Search for a one-way flight using SerpAPI Google Flights.

    Args:
        departure_id: Airport code (e.g., "JFK", "LAX", "CDG") or location identifier
        arrival_id: Airport code (e.g., "LHR", "SFO", "NRT") or location identifier
        outbound_date: Departure date in YYYY-MM-DD format
        travel_class: Travel class - must be one of: "Economy", "Premium Economy", "Business", "First"
        adults: Number of adult passengers (default: 1)
        currency: Currency code (default: USD)

    Returns:
        Flight search results including available flights, prices, airlines, and booking links
    """
    client = SerpApiClient()

    # Map travel class names to SerpAPI codes
    class_mapping = {
        "Economy": 1,
        "Premium Economy": 2,
        "Business": 3,
        "First": 4,
    }

    travel_class_code = class_mapping.get(travel_class, 1)

    return client.search_flights(
        departure_id=departure_id,
        arrival_id=arrival_id,
        outbound_date=outbound_date,
        return_date=None,
        currency=currency,
        adults=adults,
        travel_class=travel_class_code,
    )


@function_tool
def search_round_trip_flight(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str,
    travel_class: str = "Economy",
    adults: int = 1,
    currency: str = "USD",
) -> dict[str, Any]:
    """
    Search for a round-trip flight using SerpAPI Google Flights.

    Args:
        departure_id: Airport code (e.g., "JFK", "LAX", "CDG") or location identifier
        arrival_id: Airport code (e.g., "LHR", "SFO", "NRT") or location identifier
        outbound_date: Departure date in YYYY-MM-DD format
        return_date: Return date in YYYY-MM-DD format
        travel_class: Travel class - must be one of: "Economy", "Premium Economy", "Business", "First"
        adults: Number of adult passengers (default: 1)
        currency: Currency code (default: USD)

    Returns:
        Flight search results including available flights, prices, airlines, and booking links
    """
    client = SerpApiClient()

    # Map travel class names to SerpAPI codes
    class_mapping = {
        "Economy": 1,
        "Premium Economy": 2,
        "Business": 3,
        "First": 4,
    }

    travel_class_code = class_mapping.get(travel_class, 1)

    return client.search_flights(
        departure_id=departure_id,
        arrival_id=arrival_id,
        outbound_date=outbound_date,
        return_date=return_date,
        currency=currency,
        adults=adults,
        travel_class=travel_class_code,
    )


@function_tool
def search_airports(query: str, gl: str = "us", hl: str = "en") -> dict[str, Any]:
    """
    Search for airports and locations to get the correct airport codes.

    Args:
        query: Search query (e.g., "New York", "London", "JFK")
        gl: Country code (default: us)
        hl: Language code (default: en)

    Returns:
        List of airports and locations matching the query with their codes
    """
    client = SerpApiClient()
    return client.search_airports(query=query, gl=gl, hl=hl)
