"""StoryQueryAgent definition."""
from agents.agent import Agent
from .tools import query_cinegraph_core, get_character_knowledge, detect_contradictions

class StoryQueryAgent(Agent):
    """Natural language query agent for story questions."""

    name = "Story Query Assistant"
    instructions = """
    You help RPG Maker creators ask questions about their stories in natural language.
    Convert user questions into CineGraph analysis requests.
    """
    tools = [query_cinegraph_core, get_character_knowledge, detect_contradictions]
