"""StoryDebuggingAgent definition."""
from agents.agent import Agent
from .tools import query_cinegraph_core, get_character_knowledge, detect_contradictions

class StoryDebuggingAgent(Agent):
    """Assist users in debugging story issues systematically."""

    name = "Story Debugging Assistant"
    instructions = """
    You help users identify and fix complex story issues, guide them through
    debugging workflows, and suggest systematic approaches to story problems.
    """
    tools = [query_cinegraph_core, get_character_knowledge, detect_contradictions]
