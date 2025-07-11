"""RPGMakerAgent definition."""
from agents.agent import Agent
from .tools import query_cinegraph_core, get_character_knowledge, detect_contradictions

class RPGMakerAgent(Agent):
    """Assist with exporting analysis to RPG Maker formats."""

    name = "RPG Maker Integration Assistant"
    instructions = """
    You help users export CineGraph analysis results to RPG Maker formats
    and integrate story consistency checks into their development workflow.
    """
    tools = [query_cinegraph_core, get_character_knowledge, detect_contradictions]
