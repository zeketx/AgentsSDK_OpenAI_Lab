from typing import Any
import os
import httpx


class GoogleJobsClient:
    """Client for SerpAPI Google Jobs search service."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEY not provided or found in environment")
        self.base_url = "https://serpapi.com/search"

    async def search_jobs(
        self,
        query: str,
        location: str | None = None,
        hl: str = "en",
        gl: str = "us",
        google_domain: str = "google.com",
        next_page_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Search for jobs using Google Jobs via SerpAPI.

        Args:
            query: Search query (e.g., "Software Engineer", "Barista")
            location: Geographic location (e.g., "Austin, Texas, United States")
            hl: Language code (default: en)
            gl: Country code (default: us)
            google_domain: Google domain to use (default: google.com)
            next_page_token: Token for pagination (from previous response)

        Returns:
            Job search results including jobs_results, filters, and pagination info
        """
        params = {
            "engine": "google_jobs",
            "q": query,
            "hl": hl,
            "gl": gl,
            "google_domain": google_domain,
            "api_key": self.api_key,
        }

        if location:
            params["location"] = location

        if next_page_token:
            params["next_page_token"] = next_page_token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()

    async def search_jobs_with_filters(
        self,
        query: str,
        location: str | None = None,
        job_type: str | None = None,
        date_posted: str | None = None,
        hl: str = "en",
        gl: str = "us",
    ) -> dict[str, Any]:
        """
        Search for jobs with common filter options.

        Args:
            query: Search query
            location: Geographic location
            job_type: Job type filter (e.g., "full time", "part time", "contract", "internship")
            date_posted: Date posted filter (e.g., "yesterday", "last 3 days", "last week", "last month")
            hl: Language code
            gl: Country code

        Returns:
            Job search results with applied filters
        """
        # Build query with filters
        filtered_query = query

        if job_type:
            filtered_query += f" {job_type}"

        if date_posted:
            if date_posted.lower() == "yesterday":
                filtered_query += " since yesterday"
            elif date_posted.lower() in ["last 3 days", "3 days"]:
                filtered_query += " in the last 3 days"
            elif date_posted.lower() in ["last week", "week"]:
                filtered_query += " in the last week"
            elif date_posted.lower() in ["last month", "month"]:
                filtered_query += " in the last month"

        return await self.search_jobs(
            query=filtered_query,
            location=location,
            hl=hl,
            gl=gl,
        )
