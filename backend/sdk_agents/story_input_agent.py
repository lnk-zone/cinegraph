"""StoryInputAgent definition."""
from agents.agent import Agent
from .tools import query_cinegraph_core, get_character_knowledge, detect_contradictions

class StoryInputAgent(Agent):
    """Guide users through story input with validation."""

    name = "Story Input Assistant"
    instructions = """
    You guide users through story input, help format content, and provide
    real-time feedback during story creation.
    """
    tools = [query_cinegraph_core, get_character_knowledge, detect_contradictions]
