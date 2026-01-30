import asyncio
import os
import sys

# Allow running from project root: python -m app.main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import Runner  # From openai-agents-sdk package
from app.agents.orchestrator import orchestrator_agent
from app.core.config import get_model_config


async def main():
    print("🤖 Agent System Initialized. Type 'exit' to quit.")

    # Initialize the shared configuration
    # By default, this looks for OPENAI_API_KEY in environment variables
    config = get_model_config()

    # We maintain a conversation context
    # In a real app, you might persist this or manage it differently
    context = None

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            # Run the agent system
            # We start with the orchestrator_agent
            result = await Runner.run(
                orchestrator_agent, user_input, config=config, context=context
            )

            # Update context for the next turn (maintains conversation history)
            context = result.context

            # Print the final response from whichever agent handled it
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
