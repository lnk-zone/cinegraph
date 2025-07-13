import sys
import os
import types
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from game.models import RPGCharacter, CharacterStats

# Ensure project modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Stub agents package to satisfy imports if needed
import agents as local_agents

agents_pkg = local_agents
class Runner:
    @staticmethod
    async def run(starting_agent, input, context=None, max_turns=1):
        raise NotImplementedError

def handoff(agent):
    return agent

agents_pkg.Runner = Runner
agents_pkg.handoff = handoff
sys.modules["agents"] = agents_pkg

agent_base = types.ModuleType("agents.agent")
class Agent:
    def __init__(self):
        self.handoffs = []

agent_base.Agent = Agent
sys.modules.setdefault("agents.agent", agent_base)

tool_mod = types.ModuleType("agents.tool")
tool_mod.function_tool = lambda f: f
sys.modules.setdefault("agents.tool", tool_mod)

from app.main import app


@pytest.fixture
def client(rpg_graphiti_store):
    with patch("app.main.graphiti_manager.initialize", AsyncMock()), \
         patch("app.main.cinegraph_agent.initialize", AsyncMock()), \
         patch("app.main.alert_manager.start_listening", AsyncMock()):
        test_client = TestClient(app)
        yield test_client




def test_character_generation_and_enhancement(client, rpg_graphiti_store):
    project_data = {"name": "Demo", "version": "MZ", "genre": "fantasy"}
    resp = client.post("/api/rpg-projects", json=project_data)
    project_id = resp.json()["project_id"]

    story = {"story_id": "s1", "content": "Hero story"}
    client.post(f"/api/rpg-projects/{project_id}/sync-story", json=story)

    with patch("app.main.StoryCharacterEnhancer") as MockEnh:
        mock_enh = MockEnh.return_value
        mock_enh.enhance_characters = AsyncMock(return_value=[
            RPGCharacter(
                name="Alice",
                level=1,
                stats=CharacterStats(hp=100),
                knowledge_state=[],
            )
        ])

        resp = client.post(f"/api/rpg-projects/{project_id}/characters/generate-stats")
        assert resp.status_code == 200
        assert len(rpg_graphiti_store[project_id]["characters"]) == 1
        mock_enh.enhance_characters.assert_called_once()

    with patch("app.main.StoryCharacterEnhancer") as MockEnh:
        mock_enh = MockEnh.return_value
        mock_enh.enhance_characters = AsyncMock(return_value=[
            RPGCharacter(
                name="Alice",
                level=2,
                stats=CharacterStats(hp=150),
                knowledge_state=[{"id": "k1", "content": "New"}],
            )
        ])

        resp = client.post(
            f"/api/rpg-projects/{project_id}/characters/Alice/enhance-from-story"
        )
        assert resp.status_code == 200
        char = rpg_graphiti_store[project_id]["characters"][0]
        assert char.level == 2
        assert char.stats.hp == 150
        mock_enh.enhance_characters.assert_called_once()


def test_character_knowledge_state_endpoints(client, rpg_graphiti_store):
    project_data = {"name": "Demo2", "version": "MZ", "genre": "fantasy"}
    resp = client.post("/api/rpg-projects", json=project_data)
    project_id = resp.json()["project_id"]

    char = {"name": "Bob"}
    resp = client.post(f"/api/rpg-projects/{project_id}/characters", json=char)
    assert resp.status_code == 200

    resp = client.get(f"/api/rpg-projects/{project_id}/characters/Bob/knowledge-state")
    assert resp.status_code == 200
    assert resp.json()["knowledge_state"] == []

    new_knowledge = [{"id": "k1", "content": "Bob knows"}]
    resp = client.put(
        f"/api/rpg-projects/{project_id}/characters/Bob/knowledge-state",
        json=new_knowledge,
    )
    assert resp.status_code == 200
    assert rpg_graphiti_store[project_id]["characters"][0].knowledge_state == new_knowledge
