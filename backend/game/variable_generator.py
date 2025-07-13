from __future__ import annotations

"""Utility for generating RPG variables and switches from story data."""

from typing import List, Dict, Any

from .models import (
    RPGVariable,
    RPGSwitch,
    VariableScope,
    VariableDataType,
    SwitchScope,
)


class StoryVariableGenerator:
    """Generate RPG variables and switches using a CineGraphAgent."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def generate_variables(self, story_id: str) -> List[RPGVariable]:
        """Fetch variable data via the agent and return ``RPGVariable`` objects."""
        query = "MATCH (v:RPGVariable {story_id: $story_id}) RETURN v"
        result = await self.agent.graph_query(query, {"story_id": story_id})
        variables: List[RPGVariable] = []
        if result.get("success"):
            for item in result.get("data", []):
                data = item.get("v", item)
                variables.append(RPGVariable(**data))
        return variables

    async def generate_switches(self, story_id: str) -> List[RPGSwitch]:
        """Fetch switch data via the agent and return ``RPGSwitch`` objects."""
        query = "MATCH (s:RPGSwitch {story_id: $story_id}) RETURN s"
        result = await self.agent.graph_query(query, {"story_id": story_id})
        switches: List[RPGSwitch] = []
        if result.get("success"):
            for item in result.get("data", []):
                data = item.get("s", item)
                switches.append(RPGSwitch(**data))
        return switches
