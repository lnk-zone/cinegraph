"""InconsistencyExplainerAgent definition."""
from agents.agent import Agent
from .tools import query_cinegraph_core, get_character_knowledge, detect_contradictions

class InconsistencyExplainerAgent(Agent):
    """Explain story contradictions with fix suggestions."""

    name = "Inconsistency Explainer"
    instructions = """
    You explain story inconsistencies in clear, actionable terms for RPG Maker creators.
    Provide specific suggestions for fixing contradictions.
    """
    tools = [query_cinegraph_core, get_character_knowledge, detect_contradictions]
