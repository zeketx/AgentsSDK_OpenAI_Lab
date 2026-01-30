import os
from dotenv import load_dotenv
from agents import (
    AsyncOpenAI,
    OpenAIChatCompletionsModel,
)  # From openai-agents-sdk package
from agents.run import RunConfig  # From openai-agents-sdk package

load_dotenv()


def get_model_config(model_name: str = "gpt-4o") -> RunConfig:
    """
    Returns a centralized RunConfig for agents.
    Modify this to switch providers (e.g. Gemini, OpenRouter) or default models.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found in environment variables.")

    # Provider setup (Standard OpenAI)
    client = AsyncOpenAI(api_key=api_key)

    # Model setup
    model = OpenAIChatCompletionsModel(
        openai_client=client,
        model=model_name,
    )

    return RunConfig(
        model=model,
        model_provider=client,
        tracing_disabled=True,  # Set to False if you want verbose tracing
    )
