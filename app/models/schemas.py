"""Pydantic models for agent tools and API requests."""

from typing import Optional
from pydantic import BaseModel, Field


class ScrapeSelectors(BaseModel):
    """CSS selectors for extracting specific elements from web pages."""

    title: Optional[str] = Field(None, description="CSS selector for page title")
    content: Optional[str] = Field(None, description="CSS selector for main content")
    links: Optional[str] = Field(None, description="CSS selector for links")
    images: Optional[str] = Field(None, description="CSS selector for images")

    model_config = {"json_schema_extra": {"additionalProperties": False}}


class ScrapeRequest(BaseModel):
    """Request model for web scraping."""

    url: str = Field(..., description="URL to scrape")
    format: str = Field(
        default="markdown", description="Output format (markdown, html, text)"
    )
    selectors: Optional[ScrapeSelectors] = Field(
        None, description="Optional CSS selectors for specific extraction"
    )

    model_config = {"json_schema_extra": {"additionalProperties": False}}


class ScrapeResponse(BaseModel):
    """Response model for web scraping results."""

    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    text_content: str
    links: list[str] = []
    extracted: Optional[dict] = None
    cache_status: str = "miss"

    model_config = {"json_schema_extra": {"additionalProperties": False}}
