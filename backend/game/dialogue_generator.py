from __future__ import annotations

"""Utility for generating dialogue trees from story interactions."""

from typing import Any

from .models import DialogueTree
from .relationship_analyzer import CharacterRelationshipAnalyzer


class StoryDialogueGenerator:
    """Generate ``DialogueTree`` objects using a CineGraphAgent."""

    def __init__(self, agent: Any, relationship_analyzer: CharacterRelationshipAnalyzer) -> None:
        self.agent = agent
        self.relationship_analyzer = relationship_analyzer

    async def generate_dialogue_from_story_interaction(
        self, story_id: str, interaction_id: str
    ) -> DialogueTree:
        """Generate a dialogue tree based on a story interaction."""
        relationships = await self.relationship_analyzer.analyze_relationships(story_id)
        data = await self.agent.generate_dialogue_from_story_interaction(
            story_id, interaction_id, relationships
        )
        return DialogueTree(**data)
