"""Tests for StoryQuestGenerator."""

import os
import sys
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from game.quest_generator import StoryQuestGenerator
from game.models import RPGQuest, QuestType, QuestStatus


@pytest.mark.asyncio
async def test_generate_quest_from_event():
    agent = Mock()
    agent.generate_quest_from_story_event = AsyncMock(return_value={
        "name": "Retrieve Sword",
        "quest_type": "main",
        "status": "not_started",
        "description": "Find the lost sword",
        "objectives": [],
        "rewards": ["Gold"],
        "prerequisites": []
    })

    analyzer = Mock()
    analyzer.analyze_relationships = AsyncMock(return_value=[{"from": "Alice", "to": "Bob", "type": "FRIENDS_WITH"}])

    generator = StoryQuestGenerator(agent, analyzer)
    quest = await generator.generate_quest_from_story_event("story1", "event1")

    analyzer.analyze_relationships.assert_called_once_with("story1")
    agent.generate_quest_from_story_event.assert_called_once_with(
        "story1", "event1", [{"from": "Alice", "to": "Bob", "type": "FRIENDS_WITH"}]
    )

    assert isinstance(quest, RPGQuest)
    assert quest.name == "Retrieve Sword"
    assert quest.quest_type == QuestType.MAIN
    assert quest.status == QuestStatus.NOT_STARTED
