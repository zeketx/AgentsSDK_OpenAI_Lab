"""Job search tools for the jobs agent."""

from typing import Any
from agents import function_tool
from app.services.google_jobs_client import GoogleJobsClient


@function_tool
def search_jobs(
    query: str,
    location: str | None = None,
    hl: str = "en",
    gl: str = "us",
) -> dict[str, Any]:
    """
    Search for jobs using Google Jobs via SerpAPI.

    Args:
        query: Job search query (e.g., "Software Engineer", "Barista", "Data Scientist")
        location: Optional geographic location (e.g., "Austin, Texas", "New York, NY", "Remote")
        hl: Language code (default: en)
        gl: Country code (default: us)

    Returns:
        Job search results including job listings with titles, companies, locations,
        descriptions, salaries, and application links
    """
    client = GoogleJobsClient()
    return client.search_jobs(
        query=query,
        location=location,
        hl=hl,
        gl=gl,
    )


@function_tool
def search_jobs_with_filters(
    query: str,
    location: str | None = None,
    job_type: str | None = None,
    date_posted: str | None = None,
) -> dict[str, Any]:
    """
    Search for jobs with filters for job type and date posted.

    Args:
        query: Job search query (e.g., "Software Engineer", "Barista")
        location: Optional geographic location (e.g., "Austin, Texas", "Remote")
        job_type: Job type filter. Must be one of: "full time", "part time", "contract", "internship"
        date_posted: Date posted filter. Must be one of: "yesterday", "last 3 days", "last week", "last month"

    Returns:
        Filtered job search results
    """
    client = GoogleJobsClient()
    return client.search_jobs_with_filters(
        query=query,
        location=location,
        job_type=job_type,
        date_posted=date_posted,
    )


@function_tool
def get_next_page_jobs(next_page_token: str) -> dict[str, Any]:
    """
    Get the next page of job search results using a pagination token.

    Args:
        next_page_token: Pagination token from previous search results
        (found in serpapi_pagination.next_page_token)

    Returns:
        Next page of job search results
    """
    client = GoogleJobsClient()
    return client.search_jobs(
        query="",  # Query is not needed when using next_page_token
        next_page_token=next_page_token,
    )
