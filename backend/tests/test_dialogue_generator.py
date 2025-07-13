"""Tests for StoryDialogueGenerator."""

import os
import sys
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from game.dialogue_generator import StoryDialogueGenerator
from game.models import DialogueTree


@pytest.mark.asyncio
async def test_generate_dialogue_from_interaction():
    agent = Mock()
    agent.generate_dialogue_from_story_interaction = AsyncMock(return_value={
        "id": "dlg1",
        "start_node_id": "n1",
        "nodes": [
            {"id": "n1", "speaker": "Alice", "text": "Hello", "choices": []}
        ],
        "description": "Greeting"
    })

    analyzer = Mock()
    analyzer.analyze_relationships = AsyncMock(return_value=[{"from": "Alice", "to": "Bob", "type": "FRIENDS_WITH"}])

    generator = StoryDialogueGenerator(agent, analyzer)
    dialogue = await generator.generate_dialogue_from_story_interaction("story1", "inter1")

    analyzer.analyze_relationships.assert_called_once_with("story1")
    agent.generate_dialogue_from_story_interaction.assert_called_once_with(
        "story1", "inter1", [{"from": "Alice", "to": "Bob", "type": "FRIENDS_WITH"}]
    )

    assert isinstance(dialogue, DialogueTree)
    assert dialogue.id == "dlg1"
    assert dialogue.nodes[0].text == "Hello"
