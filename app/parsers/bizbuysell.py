"""BizBuySell parser for scraping business listings."""

import json
import os
import re
import secrets
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
import httpx


BIZBUYSELL_BASE_URL = "https://www.bizbuysell.com"
RETIREMENT_KEYWORDS = [
    "retire",
    "retiring",
    "retirement",
    "ready to retire",
    "planning to retire",
    "owner ready to retire",
    "ready to sell",
    "owner retiring",
    "seller retiring",
    "owner is retiring",
    "retirement sale",
    "selling due to retirement",
    "exit due to retirement",
    "owner seeking retirement",
    "retirement plans",
    "sell due to retirement",
    "owners retiring",
    "retire and move",
]


class BizBuySellParser:
    """Parser for BizBuySell search results and detail pages."""

    def __init__(self, base_url: str = BIZBUYSELL_BASE_URL):
        self.base_url = base_url

    async def fetch_page(self, url: str, timeout: float = 30.0) -> str:
        """Fetch HTML content from URL."""
        if _use_web_unlocker() and _unlocker_token():
            return await self.fetch_page_unlocker(url, timeout=timeout)

        referer = self.base_url if url != self.base_url else "https://www.google.com/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Referer": referer,
        }

        use_unlocker = _use_web_unlocker()
        client_kwargs = {"timeout": timeout, "follow_redirects": True}

        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text

    async def fetch_page_with_metadata(
        self, url: str, timeout: float = 60.0
    ) -> tuple[str, Dict]:
        """Fetch HTML and return response metadata for logging."""
        if _use_web_unlocker() and _unlocker_token():
            token = _unlocker_token()
            zone = os.getenv("BRIGHTDATA_UNLOCKER_ZONE")
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {"zone": zone, "url": url, "format": "raw"}
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    "https://api.brightdata.com/request", headers=headers, json=payload
                )
                response.raise_for_status()
                return response.text, {"source": "unlocker"}

        html = await self.fetch_page(url, timeout=timeout)
        return html, {"source": "direct"}

    async def fetch_page_unlocker(self, url: str, timeout: float = 60.0) -> str:
        """Fetch HTML content via Bright Data Unlocker API."""
        token = _unlocker_token()
        if not token:
            raise RuntimeError("BRIGHTDATA_UNLOCKER_API_TOKEN is not set")

        zone = os.getenv("BRIGHTDATA_UNLOCKER_ZONE")
        if not zone:
            raise RuntimeError("BRIGHTDATA_UNLOCKER_ZONE is not set")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {"zone": zone, "url": url, "format": "raw"}

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.brightdata.com/request", headers=headers, json=payload
            )
            response.raise_for_status()
            return response.text

    async def fetch_page_playwright(self, url: str, timeout: float = 30.0) -> str:
        """Fetch HTML content using Playwright when blocked."""
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright"
            ) from exc

        use_unlocker = _use_web_unlocker()
        proxy_url = _build_brightdata_proxy_url(use_unlocker=use_unlocker)
        proxy_config = _build_brightdata_proxy_config(
            proxy_url, use_session=True, use_unlocker=use_unlocker
        )

        async with async_playwright() as p:
            launch_kwargs: Dict[str, Any] = {"headless": True}
            if proxy_config:
                launch_kwargs["proxy"] = proxy_config  # type: ignore[assignment]
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
            content = await page.content()
            await context.close()
            await browser.close()
            return content

    def parse_search_results(
        self, html: str, base_url: Optional[str] = None
    ) -> List[Dict]:
        """Parse BizBuySell search results page."""
        if base_url is None:
            base_url = self.base_url

        soup = BeautifulSoup(html, "html.parser")
        listings: List[Dict] = []

        listing_selectors = ["a.diamond", "a.showcase", "a.basic"]
        listing_elements = []
        for selector in listing_selectors:
            listing_elements.extend(soup.select(selector))

        seen = set()
        unique_elements = []
        for element in listing_elements:
            element_key = element.get("id", "") or element.get("href", "")
            if isinstance(element_key, list):
                element_key = element_key[0] if element_key else ""
            if element_key and element_key not in seen:
                seen.add(element_key)
                unique_elements.append(element)

        for element in unique_elements:
            listing = self._extract_listing_from_element(element, base_url)
            if listing:
                listings.append(listing)

        return listings

    def parse_detail_page(self, html: str) -> Dict:
        """Parse detail page for listing metadata."""
        soup = BeautifulSoup(html, "html.parser")

        json_ld = _extract_json_ld(soup)
        json_description = _extract_json_ld_description(json_ld)
        json_reason = _extract_reason_from_text(json_description)

        full_description = _extract_text_from_candidates(
            soup,
            [
                "#listing-description",
                ".listing-description",
                ".business-description",
                "section.description",
                "div.description",
                ".listingProfile_description",
            ],
        )
        if not full_description:
            full_description = json_description

        detailed_location = _extract_text_from_candidates(
            soup, [".location", ".location-title", "#location", ".cityState"]
        )

        reason_for_selling = _extract_labeled_value(
            soup, ["Reason for Selling", "Reason for sale", "Reason for Selling?"]
        )
        if not reason_for_selling:
            reason_for_selling = json_reason

        kv_pairs = _extract_key_value_pairs(soup)
        financial_details = kv_pairs or None

        years_in_business = _find_kv_value(
            kv_pairs, ["Years in Business", "Years in business"]
        )
        employees = _find_kv_value(
            kv_pairs, ["Employees", "Number of Employees", "# Employees"]
        )
        inventory_value = _find_kv_value(kv_pairs, ["Inventory", "Inventory Value"])
        training_value = _find_kv_value(kv_pairs, ["Training", "Training Provided"])
        real_estate_value = _find_kv_value(
            kv_pairs, ["Real Estate", "Real Estate Included"]
        )

        training_included = _parse_yes_no(training_value)
        real_estate_included = _parse_yes_no(real_estate_value)

        return {
            "full_description": full_description,
            "financial_details": financial_details,
            "years_in_business": years_in_business,
            "employees": employees,
            "real_estate_included": real_estate_included,
            "inventory_value": inventory_value,
            "training_included": training_included,
            "detailed_location": detailed_location,
            "reason_for_selling": reason_for_selling,
        }

    def find_next_page_url(self, html: str, current_url: str) -> Optional[str]:
        """Detect the next page URL from pagination controls."""
        soup = BeautifulSoup(html, "html.parser")
        next_link = (
            soup.select_one("a[rel='next']")
            or soup.select_one("a.next")
            or soup.select_one("li.next a")
            or soup.select_one("a[aria-label='Next']")
        )
        if next_link and next_link.get("href"):
            next_href = next_link.get("href")
            if isinstance(next_href, list):
                next_href = next_href[0] if next_href else ""
            if next_href:
                return urljoin(self.base_url, next_href)

        parsed = urlparse(current_url)
        query = parse_qs(parsed.query)
        current_page = int(query.get("page", ["1"])[0])
        query["page"] = [str(current_page + 1)]
        new_query = urlencode(query, doseq=True)
        next_url = urlunparse(parsed._replace(query=new_query))
        if next_url != current_url:
            return next_url
        return None

    def _extract_listing_from_element(self, element, base_url: str) -> Optional[Dict]:
        """Extract listing data using provided CSS selectors."""
        try:
            href = element.get("href", "")
            if isinstance(href, list):
                href = href[0] if href else ""
            if not href:
                return None

            full_url = urljoin(base_url, href)
            external_id = element.get("id", "")
            if not external_id:
                external_id = self._extract_id_from_url(full_url)

            title_elem = element.select_one("span.title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            business_category = self._extract_category_from_title(title)

            asking_price = None
            asking_price_raw = ""
            price_elem = element.select_one(".asking-price, .asking-price-mobile")
            if price_elem:
                asking_price_raw = price_elem.get_text(strip=True)
                asking_price = self._parse_price(asking_price_raw)

            location_city = ""
            location_state = ""
            location_raw = ""
            location_elem = element.select_one("p.location")
            if location_elem:
                location_raw = location_elem.get_text(strip=True)
                location_city, location_state = self._parse_location(location_raw)

            cash_flow = ""
            cash_flow_elem = element.select_one("p.cash-flow, p.cash-flow-on-mobile")
            if cash_flow_elem:
                cash_text = cash_flow_elem.get_text(strip=True)
                cash_flow = self._extract_cash_flow(cash_text)

            seller_reason_raw = ""
            is_retirement_listing = False
            desc_elem = element.select_one("p.description")
            if desc_elem:
                seller_reason_raw = desc_elem.get_text(strip=True)
                is_retirement_listing = self._detect_retirement_keywords(
                    seller_reason_raw
                )

            if not is_retirement_listing:
                is_retirement_listing = self._detect_retirement_keywords(title)

            return {
                "external_id": external_id or full_url,
                "title": title,
                "business_category": business_category,
                "asking_price": asking_price,
                "asking_price_raw": asking_price_raw,
                "location_city": location_city,
                "location_state": location_state,
                "location_raw": location_raw,
                "revenue": "",
                "cash_flow": cash_flow,
                "seller_reason_raw": seller_reason_raw,
                "url": full_url,
                "is_retirement_listing": is_retirement_listing,
            }

        except Exception as exc:
            print(f"Error parsing listing element: {exc}")
            return None

    def _extract_category_from_title(self, title: str) -> str:
        """Extract business category from title."""
        common_categories = [
            "Restaurant",
            "Liquor Store",
            "Convenience Store",
            "Gas Station",
            "Retail",
            "Auto Repair",
            "Dental Practice",
            "Medical Practice",
            "Manufacturing",
            "Distribution",
            "Service",
            "Technology",
            "E-commerce",
            "Online Business",
            "Franchise",
            "Cafe",
            "Bar",
            "Hotel",
            "Motel",
            "Storage",
            "Laundromat",
            "Car Wash",
            "Fitness",
            "Gym",
            "Salon",
            "Spa",
            "Construction",
            "Landscaping",
        ]

        title_lower = title.lower()
        for category in common_categories:
            if category.lower() in title_lower:
                return category

        words = title.split()
        if len(words) >= 2:
            return " ".join(words[:2])
        return ""

    def _parse_price(self, price_text: str) -> Optional[int]:
        """Parse price string to integer."""
        if not price_text:
            return None

        price_text = price_text.strip()
        if "million" in price_text.lower():
            match = re.search(r"[\d.]+", price_text)
            if match:
                return int(float(match.group()) * 1_000_000)

        if "k" in price_text.lower():
            match = re.search(r"[\d.]+", price_text)
            if match:
                return int(float(match.group()) * 1_000)

        cleaned = re.sub(r"[^\d.]", "", price_text)
        if cleaned:
            try:
                return int(float(cleaned))
            except ValueError:
                return None
        return None

    def _parse_location(self, location_text: str) -> Tuple[str, str]:
        """Parse location string into city and state."""
        if not location_text:
            return "", ""

        parts = location_text.split(",")
        if len(parts) >= 2:
            city = parts[0].strip()
            state = parts[1].strip()
            return city, state
        return location_text.strip(), ""

    def _extract_cash_flow(self, cash_text: str) -> str:
        """Extract cash flow value from text."""
        if not cash_text:
            return ""
        cash_text = cash_text.replace("Cash Flow:", "").strip()
        return cash_text

    def _detect_retirement_keywords(self, text: str) -> bool:
        """Detect retirement-related keywords in text."""
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in RETIREMENT_KEYWORDS)

    def _extract_id_from_url(self, url: str) -> str:
        """Extract listing ID from URL if present."""
        match = re.search(r"/(\d+)/", url)
        if match:
            return match.group(1)
        return ""


def _build_brightdata_proxy_url(use_unlocker: bool = False) -> Optional[str]:
    """Build Bright Data proxy URL from environment variables."""
    direct_url = os.getenv("BRIGHTDATA_PROXY_URL")
    if direct_url:
        return _apply_zone_override_to_url(direct_url, use_unlocker)

    host = os.getenv("BRIGHTDATA_PROXY_HOST")
    port = os.getenv("BRIGHTDATA_PROXY_PORT")
    username = os.getenv("BRIGHTDATA_PROXY_USERNAME")
    password = os.getenv("BRIGHTDATA_PROXY_PASSWORD")

    if host and port and username and password:
        username = _apply_zone_override_to_username(username, use_unlocker)
        return f"http://{username}:{password}@{host}:{port}"

    return None


def _build_brightdata_proxy_config(
    proxy_url: Optional[str],
    use_session: bool = False,
    use_unlocker: bool = False,
) -> Optional[dict]:
    """Build Playwright proxy config from URL or env vars."""
    host = os.getenv("BRIGHTDATA_PROXY_HOST")
    port = os.getenv("BRIGHTDATA_PROXY_PORT")
    username = os.getenv("BRIGHTDATA_PROXY_USERNAME")
    password = os.getenv("BRIGHTDATA_PROXY_PASSWORD")

    session_suffix = f"-session-{secrets.token_hex(4)}" if use_session else ""

    if host and port:
        config = {"server": f"http://{host}:{port}"}
        if username:
            username = _apply_zone_override_to_username(username, use_unlocker)
            config["username"] = f"{username}{session_suffix}"
        if password:
            config["password"] = password
        return config

    if proxy_url:
        parsed = urlparse(proxy_url)
        if parsed.hostname and parsed.port:
            config = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
            if parsed.username:
                username = _apply_zone_override_to_username(
                    parsed.username, use_unlocker
                )
                config["username"] = f"{username}{session_suffix}"
            if parsed.password:
                config["password"] = parsed.password
            return config

    return None


def _apply_zone_override_to_username(username: str, use_unlocker: bool) -> str:
    """Replace the zone in a Bright Data username when unlocker is enabled."""
    if not use_unlocker:
        return username

    zone = os.getenv("BRIGHTDATA_UNLOCKER_ZONE")
    if not zone:
        return username

    if "-zone-" in username:
        prefix = username.split("-zone-")[0]
        suffix_parts = username.split("-zone-")
        if len(suffix_parts) > 1:
            rest = suffix_parts[1]
            tail = ""
            if "-" in rest:
                tail = "-" + rest.split("-", 1)[1]
            return f"{prefix}-zone-{zone}{tail}"

    return f"{username}-zone-{zone}"


def _apply_zone_override_to_url(proxy_url: str, use_unlocker: bool) -> str:
    if not use_unlocker:
        return proxy_url

    parsed = urlparse(proxy_url)
    if not parsed.username:
        return proxy_url

    username = _apply_zone_override_to_username(parsed.username, use_unlocker)
    password = parsed.password or ""
    host = parsed.hostname or ""
    port = parsed.port or ""
    scheme = parsed.scheme or "http"
    return f"{scheme}://{username}:{password}@{host}:{port}"


def _use_web_unlocker() -> bool:
    value = os.getenv("BRIGHTDATA_USE_WEB_UNLOCKER", "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    return _unlocker_token() is not None


def _unlocker_token() -> Optional[str]:
    return os.getenv("BRIGHTDATA_UNLOCKER_API_TOKEN")


def _extract_text_from_candidates(
    soup: BeautifulSoup, selectors: List[str]
) -> Optional[str]:
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(" ", strip=True)
            if text:
                return text
    return None


def _extract_labeled_value(soup: BeautifulSoup, labels: List[str]) -> Optional[str]:
    for label in labels:
        label_elements = soup.find_all(text=re.compile(re.escape(label), re.I))
        for element in label_elements:
            parent = element.parent
            if not parent:
                continue
            value = parent.find_next_sibling()
            if value:
                text = value.get_text(" ", strip=True)
                if text:
                    return text
    return None


def _extract_key_value_pairs(soup: BeautifulSoup) -> Dict[str, str]:
    pairs: Dict[str, str] = {}

    for row in soup.select(".listing-details .row"):
        label = row.select_one(".label, .detail-label")
        value = row.select_one(".value, .detail-value")
        if label and value:
            key = label.get_text(" ", strip=True)
            val = value.get_text(" ", strip=True)
            if key and val:
                pairs[key] = val

    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for dt, dd in zip(dts, dds):
            key = dt.get_text(" ", strip=True)
            val = dd.get_text(" ", strip=True)
            if key and val:
                pairs.setdefault(key, val)

    return pairs


def _extract_json_ld(soup: BeautifulSoup) -> List[Dict]:
    payloads = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = script.string
            if not data:
                continue
            parsed = json.loads(data)
            if isinstance(parsed, list):
                payloads.extend(parsed)
            elif isinstance(parsed, dict):
                payloads.append(parsed)
        except Exception:
            continue
    return payloads


def _extract_json_ld_description(payloads: List[Dict]) -> Optional[str]:
    for payload in payloads:
        description = payload.get("description") if isinstance(payload, dict) else None
        if description:
            return str(description).strip()
    return None


def _extract_reason_from_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    lower = text.lower()
    if "reason for sale" in lower or "reason for selling" in lower:
        start = lower.find("reason for sale")
        if start == -1:
            start = lower.find("reason for selling")
        return text[start:].strip() if start != -1 else None
    if "owner retiring" in lower or "retiring" in lower:
        return "Owner retiring"
    return None


def _find_kv_value(kv_pairs: Dict[str, str], keys: List[str]) -> Optional[str]:
    for key in keys:
        if key in kv_pairs:
            return kv_pairs[key]
    return None


def _parse_yes_no(value: Optional[str]) -> Optional[bool]:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in {"yes", "y", "included", "true"}:
        return True
    if normalized in {"no", "n", "not included", "false"}:
        return False
    return None
