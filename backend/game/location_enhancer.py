from __future__ import annotations

"""Utility for enhancing location information from story analysis."""

from typing import Any, List, Tuple

from .models import RPGLocation, LocationConnection


class StoryLocationEnhancer:
    """Enhance story locations using a CineGraph agent."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def enhance_locations(self, story_id: str) -> Tuple[List[RPGLocation], List[LocationConnection]]:
        """Generate ``RPGLocation`` and ``LocationConnection`` objects using the provided agent.

        The agent is expected to expose an ``analyze_story_locations`` method that
        returns a dictionary with ``locations`` and ``connections`` lists.
        """
        result = await self.agent.analyze_story_locations(story_id)
        locations: List[RPGLocation] = []
        connections: List[LocationConnection] = []

        for data in result.get("locations", []):
            locations.append(RPGLocation(**data))
        for data in result.get("connections", []):
            connections.append(LocationConnection(**data))

        return locations, connections
