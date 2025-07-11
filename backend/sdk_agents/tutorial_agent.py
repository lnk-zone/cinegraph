"""TutorialAgent definition."""
from agents.agent import Agent
from .tools import query_cinegraph_core, get_character_knowledge, detect_contradictions

class TutorialAgent(Agent):
    """Guide new users through CineGraph features."""

    name = "CineGraph Tutorial Assistant"
    instructions = """
    You guide new users through CineGraph features and help them understand
    story analysis concepts in an approachable way.
    """
    tools = [query_cinegraph_core, get_character_knowledge, detect_contradictions]
