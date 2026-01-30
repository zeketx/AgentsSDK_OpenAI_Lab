# Personal Assistant MVP

Minimal agent-driven assistant with a scraper microservice.

Architecture diagram: `architecture.md`

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`

## Environment

Create a `.env` file using `.env.example`:

```
OPENAI_API_KEY=your_key_here
SCRAPER_SERVICE_URL=http://localhost:8001
```

## Run the scraper service

```
uvicorn app.services.scraper_service:app --host 0.0.0.0 --port 8001
```

## Optional: run Redis for caching

If you have Redis locally:

```
redis-server
```

## Scraper limits

You can cap response size (bytes):

```
SCRAPER_MAX_BYTES=2000000
```

## Run the agent orchestrator

```
python -m app.main
```

## Example prompt

Ask the assistant to scrape a URL, for example:

```
Scrape https://example.com and summarize the page.
```
