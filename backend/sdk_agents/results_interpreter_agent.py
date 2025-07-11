"""ResultsInterpreterAgent definition."""
from agents.agent import Agent
from .tools import query_cinegraph_core, get_character_knowledge, detect_contradictions

class ResultsInterpreterAgent(Agent):
    """Translate analysis results into actionable insights."""

    name = "Analysis Results Interpreter"
    instructions = """
    You translate complex CineGraph analysis results into actionable insights
    for story creators, focusing on practical improvements.
    """
    tools = [query_cinegraph_core, get_character_knowledge, detect_contradictions]
