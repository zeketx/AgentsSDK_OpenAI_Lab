from agents import Agent, function_tool  # From openai-agents-sdk package
import httpx
import os

# Example specialized agent
# This file defines a specific role or "persona"


@function_tool
def get_research_summary(topic: str) -> str:
    """
    Simulates researching a topic.
    In a real app, this would call a search API.
    """
    return f"Research complete: {topic} is a broad subject involving X, Y, and Z."


@function_tool
async def scrape_url(
    url: str, format: str = "markdown", selectors: dict | None = None
) -> dict:
    """
    Fetch and extract content from a URL using the scraper service.
    """
    base_url = os.getenv("SCRAPER_SERVICE_URL", "http://localhost:8001")
    payload = {"url": url, "format": format, "selectors": selectors}
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(f"{base_url}/scrape", json=payload)
        response.raise_for_status()
        return response.json()


researcher_agent = Agent(
    name="Researcher",
    instructions="""You are a Researcher. 
    Your goal is to find information and summarize it concisely.
    Use your tools to gather data.""",
    tools=[get_research_summary, scrape_url],
)
