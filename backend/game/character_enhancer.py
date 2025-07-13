from __future__ import annotations

"""Utility for enhancing character information from story analysis."""

from typing import Any, List

from .models import RPGCharacter


class StoryCharacterEnhancer:
    """Enhance story characters using a CineGraph agent."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def enhance_characters(self, story_id: str) -> List[RPGCharacter]:
        """Generate ``RPGCharacter`` objects using the provided agent.

        The agent is expected to expose an ``analyze_story_characters`` method
        that returns a dictionary with a ``characters`` list. Each list item
        should be compatible with :class:`RPGCharacter`.
        """
        result = await self.agent.analyze_story_characters(story_id)
        characters: List[RPGCharacter] = []
        for data in result.get("characters", []):
            characters.append(RPGCharacter(**data))
        return characters
