"""Tests for StoryVariableGenerator."""

import os
import sys
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from game.variable_generator import StoryVariableGenerator
from game.models import (
    RPGVariable,
    RPGSwitch,
    VariableDataType,
    VariableScope,
    SwitchScope,
)


@pytest.mark.asyncio
async def test_generate_variables_and_switches():
    agent = Mock()
    agent.graph_query = AsyncMock(side_effect=[
        {
            "success": True,
            "data": [
                {
                    "name": "HeroHP",
                    "value": 50,
                    "data_type": "integer",
                    "scope": "game",
                    "description": "Hero health",
                }
            ],
        },
        {
            "success": True,
            "data": [
                {
                    "name": "DoorOpen",
                    "is_on": True,
                    "scope": "global",
                    "description": "State of the door",
                }
            ],
        },
    ])

    generator = StoryVariableGenerator(agent)

    variables = await generator.generate_variables("story1")
    switches = await generator.generate_switches("story1")

    assert agent.graph_query.call_count == 2

    assert len(variables) == 1
    var = variables[0]
    assert isinstance(var, RPGVariable)
    assert var.name == "HeroHP"
    assert var.value == 50
    assert var.data_type == VariableDataType.INTEGER
    assert var.scope == VariableScope.GAME

    assert len(switches) == 1
    sw = switches[0]
    assert isinstance(sw, RPGSwitch)
    assert sw.name == "DoorOpen"
    assert sw.is_on is True
    assert sw.scope == SwitchScope.GLOBAL
