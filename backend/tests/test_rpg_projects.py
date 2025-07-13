import os
import sys
import types
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Ensure project modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import local agents package then stub required submodules
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

from app.main import app, rpg_projects


@pytest.fixture
def client():
    with patch("app.main.graphiti_manager.initialize", AsyncMock()), \
         patch("app.main.cinegraph_agent.initialize", AsyncMock()), \
         patch("app.main.alert_manager.start_listening", AsyncMock()):
        test_client = TestClient(app)
        yield test_client


@pytest.fixture(autouse=True)
def clear_projects():
    rpg_projects.clear()
    yield
    rpg_projects.clear()


def test_project_workflow(client):
    project_data = {"name": "Demo", "version": "MZ", "genre": "fantasy"}
    resp = client.post("/api/rpg-projects", json=project_data)
    assert resp.status_code == 200
    result = resp.json()
    project_id = result["project_id"]
    assert project_id in rpg_projects

    story = {"story_id": "s1", "content": "Once upon a time"}
    resp = client.post(f"/api/rpg-projects/{project_id}/sync-story", json=story)
    assert resp.status_code == 200
    assert rpg_projects[project_id]["stories"]["s1"] == "Once upon a time"

    config = {
        "project": project_data,
        "target_version": "MZ",
        "include_assets": True,
        "include_events": True,
        "package_format": "zip",
        "output_path": "./export",
        "validate_before_export": True,
        "validation_level": "basic",
    }
    resp = client.post(
        f"/api/rpg-projects/{project_id}/export-configs", json=config
    )
    assert resp.status_code == 200

    resp = client.get(f"/api/rpg-projects/{project_id}/export-configs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["export_configs"], list)
    assert len(data["export_configs"]) == 1
