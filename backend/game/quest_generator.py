from __future__ import annotations

"""Utility for generating quests from analyzed story events."""

from typing import Any

from .models import RPGQuest
from .relationship_analyzer import CharacterRelationshipAnalyzer


class StoryQuestGenerator:
    """Generate ``RPGQuest`` objects using a CineGraphAgent."""

    def __init__(self, agent: Any, relationship_analyzer: CharacterRelationshipAnalyzer) -> None:
        self.agent = agent
        self.relationship_analyzer = relationship_analyzer

    async def generate_quest_from_story_event(self, story_id: str, event_id: str) -> RPGQuest:
        """Generate a quest based on a story event.

        The agent should expose ``generate_quest_from_story_event`` which takes
        ``story_id``, ``event_id`` and a list of character relationships.
        """
        relationships = await self.relationship_analyzer.analyze_relationships(story_id)
        data = await self.agent.generate_quest_from_story_event(story_id, event_id, relationships)
        return RPGQuest(**data)
