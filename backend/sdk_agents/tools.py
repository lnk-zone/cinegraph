"""Helper tool wrappers for SDK agents.

These wrappers expose a minimal interface for accessing CineGraph core
functionality via :class:`GraphitiManager`.
"""
from __future__ import annotations

import os
from agents.tool import function_tool
from core.graphiti_manager import GraphitiManager

# Global GraphitiManager instance used by tools
_graphiti_manager = GraphitiManager()

async def _ensure_connected() -> None:
    """Ensure the GraphitiManager is initialized."""
    if _graphiti_manager.client is None:
        await _graphiti_manager.initialize()

@function_tool
async def query_cinegraph_core(query: str, story_id: str) -> dict:
    """Tool for SDK agents to access the core analysis engine."""
    await _ensure_connected()
    return await _graphiti_manager._run_cypher_query(query)

DEFAULT_STORY_ID = os.getenv("DEFAULT_STORY_ID", "demo_story")

@function_tool
async def get_character_knowledge(character: str, timestamp: str) -> dict:
    """Tool to get character knowledge at specific time."""
    await _ensure_connected()
    knowledge = await _graphiti_manager.get_character_knowledge(
        DEFAULT_STORY_ID, character, timestamp, user_id="sdk_agent"
    )
    return knowledge.model_dump() if hasattr(knowledge, "model_dump") else knowledge.__dict__

@function_tool
async def detect_contradictions(story_id: str) -> list:
    """Tool to run contradiction detection."""
    await _ensure_connected()
    result = await _graphiti_manager.detect_contradictions(story_id, user_id="sdk_agent")
    return result.get("result", [])
