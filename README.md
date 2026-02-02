# Personal Assistant MVP

Multi-agent AI assistant with specialized agents for research, travel planning, job search, and Gmail inbox management.

## Features

- **🔍 Research Agent** - Web scraping and research tasks
- **✈️ Travel Agent** - Flight search via SerpAPI Google Flights (one-way & round-trip)
- **💼 Jobs Agent** - Job search via SerpAPI Google Jobs with filters
- **📧 Gmail Agent** - Inbox organization, email categorization, and label management

## Architecture

See detailed architecture diagrams in `architecture.md`

```mermaid
flowchart LR
    user[User] --> orchestrator[Orchestrator Agent]

    orchestrator --> researcher[Researcher Agent]
    orchestrator --> travel[Travel Agent]
    orchestrator --> jobs[Jobs Agent]
    orchestrator --> gmail[Gmail Agent]

    researcher --> scraper[Scraper Service]
    scraper --> unlocker[Bright Data Web Unlocker]
    unlocker --> web[Web Pages]
    scraper --> sqlite[(SQLite)]

    travel --> serp[SerpAPI Client]
    serp --> serpapi[SerpAPI/Google Flights]

    jobs --> jobs_client[Google Jobs Client]
    jobs_client --> serpapi

    gmail --> gmail_client[Gmail Client]
    gmail_client --> gmail_api[Gmail API]

    orchestrator --> user
```

```
User → Orchestrator Agent → Specialist Agents (Researcher/Travel/Jobs/Gmail) → Services → APIs
```

## Requirements

- Python 3.10+
- OpenAI API key
- SerpAPI account (for flights and jobs)
- Google Cloud account with Gmail API enabled (for Gmail features)
- `pip install -r requirements.txt`

## Environment Setup

Create a `.env` file using `.env.example`:

```
OPENAI_API_KEY=your_key_here
SERPAPI_API_KEY=your_serpapi_key_here
SCRAPER_SERVICE_URL=http://localhost:8001
SCRAPER_MAX_BYTES=2000000

# Bright Data proxy (for BizBuySell scraping)
BRIGHTDATA_PROXY_URL=http://username:password@host:port
# Or use separate fields
BRIGHTDATA_PROXY_HOST=host
BRIGHTDATA_PROXY_PORT=port
BRIGHTDATA_PROXY_USERNAME=username
BRIGHTDATA_PROXY_PASSWORD=password

# Bright Data Web Unlocker
BRIGHTDATA_USE_WEB_UNLOCKER=true
BRIGHTDATA_UNLOCKER_ZONE=web_unlocker
BRIGHTDATA_UNLOCKER_API_TOKEN=your_unlocker_api_token
```

### Getting API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **SerpAPI**: https://serpapi.com (required for flights and jobs search)
- **Google/Gmail**: 
  1. Go to [Google Cloud Console](https://console.cloud.google.com)
  2. Create a project and enable **Gmail API**
  3. Create OAuth 2.0 credentials (Desktop application type)
  4. Download `gmail_credentials.json` and place in project root
  5. Add your email as a **Test User** in OAuth consent screen

## Running the Services

### 1. Scraper Service (Optional - for web scraping)

```bash
uvicorn app.services.scraper_service:app --host 0.0.0.0 --port 8001
```

### 2. Redis Cache (Optional)

Redis is no longer required for scraping.

### 3. Main Agent Orchestrator

```bash
python -m app.main
```

## Usage Examples

### Research & Web Scraping

```
Scrape https://example.com and summarize the page.
```

### Flight Search

```
Find one-way flights from JFK to LHR on 2025-03-15
Search for round-trip flights from Los Angeles to Tokyo, business class
What airports are near Paris?
```

### Job Search

```
Find software engineer jobs in San Francisco
Search for remote marketing positions posted this week
Show me full-time barista jobs in Austin, Texas
```

### Gmail Management

```
Show me my Gmail labels
Find all emails from github.com
Create a "Newsletters" label and apply to all newsletter emails
Categorize all LinkedIn emails into a "Social" label
Show me unread emails from last month
```

## Project Structure

```
app/
├── agents/
│   ├── orchestrator.py      # Main entry point, routes to specialists
│   ├── researcher.py        # Web scraping & research agent
│   ├── travel_agent.py      # Flight search specialist
│   ├── jobs_agent.py        # Job search specialist
│   └── gmail_agent.py       # Gmail inbox management specialist
├── services/
│   ├── scraper_service.py   # FastAPI web scraping microservice
│   ├── serpapi_client.py    # Google Flights API client
│   ├── google_jobs_client.py # Google Jobs API client
│   └── gmail_client.py      # Gmail API client (OAuth2)
├── tools/
│   ├── flight_tools.py      # Flight search tool functions
│   ├── jobs_tools.py        # Job search tool functions
│   └── gmail_tools.py       # Gmail management tool functions
├── models/
│   └── schemas.py           # Pydantic models for type safety
├── core/
│   └── config.py            # Model configuration
└── main.py                  # CLI entry point
```

## Agent Capabilities

### Orchestrator Agent
- Routes user requests to appropriate specialist agents
- Maintains conversation context
- Synthesizes specialist responses for the user

### Researcher Agent
- `scrape_url()` - Extract content from web pages
- `get_research_summary()` - Research topics (simulated)
- Integrates with Scraper Service and Bright Data Unlocker when enabled

### Travel Agent
- `search_one_way_flight()` - Search one-way flights
- `search_round_trip_flight()` - Search round-trip flights  
- `search_airports()` - Find airport codes
- Supports filters: travel class, passengers, currency

### Jobs Agent
- `search_jobs()` - Basic job search by query and location
- `search_jobs_with_filters()` - Filtered search (job type, date posted)
- `get_next_page_jobs()` - Paginate through results
- Returns: job title, company, location, salary, description, apply links

### Gmail Agent
- `list_gmail_labels()` - List all Gmail labels
- `create_gmail_label()` - Create new labels with custom colors
- `categorize_emails_by_sender()` - Auto-categorize by domain (e.g., github.com → "GitHub")
- `search_emails_by_query()` - Search with Gmail query syntax
- `apply_label_to_matching_emails()` - Bulk label application with chunking
- **Safety**: Read and label operations only - no delete or archive
- **Authentication**: OAuth2 with browser flow (one-time setup)

## Configuration

### Scraper Service Limits

Control response size to prevent memory issues:

```
SCRAPER_MAX_BYTES=2000000  # 2MB default
```

### Redis Cache

Redis is not used by the scraper service.

## Testing

Test individual services:

```python
# Test Google Jobs API
python -c "from app.services.google_jobs_client import GoogleJobsClient; 
import asyncio; 
client = GoogleJobsClient(); 
result = asyncio.run(client.search_jobs('software engineer', 'San Francisco')); 
print(f'Found {len(result[\"jobs_results\"])} jobs')"

# Test Google Flights API  
python -c "from app.services.serpapi_client import SerpApiClient; 
import asyncio; 
client = SerpApiClient(); 
result = asyncio.run(client.search_flights('JFK', 'LHR', '2025-03-15')); 
print(f'Found {len(result[\"best_flights\"])} flights')"

# Test Gmail API
python test_gmail.py
# Or programmatically:
python -c "from app.services.gmail_client import GmailClient; 
import asyncio; 
client = GmailClient(); 
client.connect(); 
labels = client.list_labels(); 
print(f'Connected! Found {len(labels)} labels')"
```

### First-Time Gmail Setup

When you run Gmail commands for the first time:

1. A browser window will open asking you to sign in to Google
2. Select your Gmail account
3. Grant permission for "Personal Assistant" to manage Gmail
4. The auth token will be saved to `gmail_token.pickle` (no more browser popups!)
5. Return to the terminal - you're ready to organize your inbox
