"""CharacterAnalysisAgent definition."""
from agents.agent import Agent
from .tools import query_cinegraph_core, get_character_knowledge, detect_contradictions

class CharacterAnalysisAgent(Agent):
    """Assist with character knowledge timelines and comparisons."""

    name = "Character Knowledge Assistant"
    instructions = """
    You help creators understand what their characters know and when they learned it.
    Explain character development and knowledge evolution clearly.
    """
    tools = [query_cinegraph_core, get_character_knowledge, detect_contradictions]
