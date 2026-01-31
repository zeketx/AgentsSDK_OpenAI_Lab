from agents import Agent  # From openai-agents-sdk package
from app.agents.researcher import researcher_agent  # Local module
from app.agents.travel_agent import travel_agent  # Local module
from app.agents.jobs_agent import jobs_agent  # Local module
from app.agents.gmail_agent import gmail_agent  # Local module

# The Orchestrator is the main entry point.
# It decides whether to handle a request directly or hand it off.

orchestrator_agent = Agent(
    name="Orchestrator",
    instructions="""You are the main Assistant.
    You manage the conversation and delegate specialized tasks to other agents.

    Use specialist tools for:
    - Research and web scraping tasks (researcher tool)
    - Flight search and travel planning (travel_agent tool)
    - Job search and career assistance (jobs_agent tool)
    - Gmail inbox organization and email categorization (gmail_agent tool)

    Always synthesize the specialist findings into a final response to the user.""",
    tools=[
        researcher_agent.as_tool(
            tool_name="researcher",
            tool_description="Researches topics and performs web scraping tasks.",
        ),
        travel_agent.as_tool(
            tool_name="travel_agent",
            tool_description="Searches for flights, finds airports, and helps with travel planning.",
        ),
        jobs_agent.as_tool(
            tool_name="jobs_agent",
            tool_description="Searches for jobs, helps with job applications, and provides career assistance.",
        ),
        gmail_agent.as_tool(
            tool_name="gmail_agent",
            tool_description="Organizes Gmail inbox, creates labels, categorizes emails by sender or query. Safe read/label operations only - no delete.",
        ),
    ],
)
