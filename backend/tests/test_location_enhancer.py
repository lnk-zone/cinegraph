"""Tests for StoryLocationEnhancer."""

import os
import sys
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from game.location_enhancer import StoryLocationEnhancer
from game.models import (
    RPGLocation,
    LocationConnection,
    LocationType,
    ConnectionType,
    Direction,
)


@pytest.mark.asyncio
async def test_enhance_locations_returns_events_and_connections():
    agent = Mock()
    agent.analyze_story_locations = AsyncMock(return_value={
        "locations": [
            {
                "name": "Town",
                "type": "town",
                "description": "A peaceful town",
                "events": ["Festival"],
            }
        ],
        "connections": [
            {
                "from_location": "Town",
                "to_location": "Forest",
                "type": "path",
                "direction": "north",
            }
        ],
    })

    enhancer = StoryLocationEnhancer(agent)
    locations, connections = await enhancer.enhance_locations("story1")

    agent.analyze_story_locations.assert_called_once_with("story1")

    assert len(locations) == 1
    loc = locations[0]
    assert isinstance(loc, RPGLocation)
    assert loc.name == "Town"
    assert loc.type == LocationType.TOWN
    assert loc.events == ["Festival"]

    assert len(connections) == 1
    conn = connections[0]
    assert isinstance(conn, LocationConnection)
    assert conn.from_location == "Town"
    assert conn.to_location == "Forest"
    assert conn.type == ConnectionType.PATH
    assert conn.direction == Direction.NORTH
