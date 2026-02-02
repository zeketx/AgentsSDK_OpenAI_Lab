import asyncio
import os
import sys

# Allow running from project root: python -m app.main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import Runner  # From openai-agents-sdk package
from fastapi import FastAPI
from app.agents.orchestrator import orchestrator_agent
from app.database import init_db
from app.scheduler.scrape_job import start_scheduler
from app.api.listings import router as listings_router


async def main():
    print("🤖 Agent System Initialized. Type 'exit' to quit.")

    init_db()
    start_scheduler()

    context = None

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            result = await Runner.run(orchestrator_agent, user_input, context=context)

            context = result.context
            print(f"\n{result.current_agent.name}: {result.final_output}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    # Ensure API key is set before starting
    if not os.getenv("OPENAI_API_KEY") and not os.path.exists(".env"):
        print("⚠️  Warning: No .env file found. Make sure OPENAI_API_KEY is set.")

    asyncio.run(main())


app = FastAPI(title="BizBuySell Listings API")
app.include_router(listings_router)
