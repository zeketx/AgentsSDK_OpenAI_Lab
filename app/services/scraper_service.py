from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from bs4 import BeautifulSoup
import httpx
import hashlib
import json
import os
import redis


app = FastAPI(title="Scraper Service")


redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
cache_ttl_seconds = int(os.getenv("SCRAPER_CACHE_TTL_SECONDS", "900"))
max_bytes = int(os.getenv("SCRAPER_MAX_BYTES", "2000000"))


class ScrapeRequest(BaseModel):
    url: HttpUrl
    format: str = "markdown"
    selectors: dict[str, str] | None = None


class ScrapeResponse(BaseModel):
    url: HttpUrl
    title: str | None
    meta_description: str | None
    text_content: str
    links: list[str]
    extracted: dict[str, str] | None
    cache_status: str


def _extract_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.stripped_strings)
    return text


def _extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    links = []
    for link in soup.find_all("a", href=True):
        href = link.get("href")
        if href:
            links.append(href)
    return links


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_page(request: ScrapeRequest) -> ScrapeResponse:
    cache_key = _cache_key(request)
    cached = None
    try:
        cached = redis_client.get(cache_key)
    except redis.RedisError:
        cached = None
    if cached:
        payload = json.loads(cached)
        return ScrapeResponse(**payload, cache_status="hit")

    headers = {
        "User-Agent": "PersonalAssistantScraper/0.1",
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(str(request.url), headers=headers)
        response.raise_for_status()

    content_length = response.headers.get("content-length")
    if content_length and int(content_length) > max_bytes:
        raise HTTPException(status_code=413, detail="Response too large")

    if len(response.content) > max_bytes:
        raise HTTPException(status_code=413, detail="Response too large")

    soup = BeautifulSoup(response.text, "html.parser")
    title = None
    if soup.title and soup.title.string:
        title = str(soup.title.string).strip()

    meta_description = None
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = str(meta_tag["content"]).strip()

    extracted = None
    if request.selectors:
        extracted = {}
        for key, selector in request.selectors.items():
            match = soup.select_one(selector)
            if match:
                extracted[key] = match.get_text(strip=True)

    text_content = _extract_text(soup)
    links = _extract_links(soup, str(request.url))

    result = ScrapeResponse(
        url=request.url,
        title=title,
        meta_description=meta_description,
        text_content=text_content,
        links=links,
        extracted=extracted,
        cache_status="miss",
    )

    try:
        redis_client.setex(cache_key, cache_ttl_seconds, result.json())
    except redis.RedisError:
        result.cache_status = "bypass"
    return result


def _cache_key(request: ScrapeRequest) -> str:
    key_payload = {
        "url": str(request.url),
        "format": request.format,
        "selectors": request.selectors,
    }
    raw = json.dumps(key_payload, sort_keys=True)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"scrape:{digest}"
