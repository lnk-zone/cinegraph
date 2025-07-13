"""Tests for StoryCharacterEnhancer."""

import os
import sys
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from game.character_enhancer import StoryCharacterEnhancer
from game.models import RPGCharacter


@pytest.mark.asyncio
async def test_enhance_characters_populates_stats_and_knowledge():
    agent = Mock()
    agent.analyze_story_characters = AsyncMock(return_value={
        "characters": [
            {
                "name": "Alice",
                "type": "hero",
                "level": 5,
                "stats": {
                    "hp": 120,
                    "mp": 30,
                    "strength": 15,
                    "agility": 12,
                    "intelligence": 14,
                    "charisma": 11,
                },
                "knowledge_state": [
                    {"id": "k1", "content": "Alice knows the prophecy"}
                ],
            }
        ]
    })

    enhancer = StoryCharacterEnhancer(agent)
    characters = await enhancer.enhance_characters("story1")

    agent.analyze_story_characters.assert_called_once_with("story1")
    assert len(characters) == 1

    char = characters[0]
    assert isinstance(char, RPGCharacter)
    assert char.name == "Alice"
    assert char.stats.hp == 120
    assert char.stats.strength == 15
    assert len(char.knowledge_state) == 1
    assert char.knowledge_state[0]["content"] == "Alice knows the prophecy"
