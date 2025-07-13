import os
import sys
import types
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from game.models import RPGLocation, LocationConnection

# Stub out graphiti_core modules used by GraphitiManager
graphiti_core = types.ModuleType("graphiti_core")
graphiti_core.Graphiti = object
nodes = types.ModuleType("graphiti_core.nodes")
nodes.EntityNode = object
nodes.EpisodicNode = object
edges = types.ModuleType("graphiti_core.edges")
edges.EntityEdge = object
sys.modules['graphiti_core'] = graphiti_core
sys.modules['graphiti_core.nodes'] = nodes
sys.modules['graphiti_core.edges'] = edges
search_mod = types.ModuleType("graphiti_core.search.search")
search_mod.SearchConfig = object
sys.modules['graphiti_core.search'] = types.ModuleType("graphiti_core.search")
sys.modules['graphiti_core.search.search'] = search_mod
neo4j = types.ModuleType("neo4j")
neo4j.AsyncGraphDatabase = object
sys.modules['neo4j'] = neo4j
celery_mod = types.ModuleType("celery")
class Celery:
    def __init__(self, *args, **kwargs):
        self.conf = types.SimpleNamespace(update=lambda *a, **k: None)
    def task(self, *a, **k):
        def wrapper(f):
            return f
        return wrapper
celery_mod.Celery = Celery
sys.modules['celery'] = celery_mod
celery_sched = types.ModuleType("celery.schedules")
celery_sched.crontab = lambda *a, **k: None
sys.modules['celery.schedules'] = celery_sched
supabase_mod = types.ModuleType("supabase")
supabase_mod.create_client = lambda *a, **k: None
supabase_mod.Client = object
sys.modules['supabase'] = supabase_mod
celery_mod.shared_task = lambda *a, **k: (lambda f: f)
jose_mod = types.ModuleType("jose")
jwt_mod = types.ModuleType("jose.jwt")
jwt_mod.encode = lambda *a, **k: ""
jwt_mod.decode = lambda *a, **k: {}
jose_mod.jwt = jwt_mod
jose_mod.JWTError = Exception
sys.modules['jose'] = jose_mod
sys.modules['jose.jwt'] = jwt_mod

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




def test_location_generation_and_enhancement(client, rpg_graphiti_store):
    project_data = {"name": "LocProj", "version": "MZ", "genre": "fantasy"}
    resp = client.post("/api/rpg-projects", json=project_data)
    project_id = resp.json()["project_id"]

    story = {"story_id": "s1", "content": "A town and a forest"}
    client.post(f"/api/rpg-projects/{project_id}/sync-story", json=story)

    with patch("app.main.StoryLocationEnhancer") as MockEnh:
        mock_enh = MockEnh.return_value
        mock_enh.enhance_locations = AsyncMock(return_value=(
            [RPGLocation(name="Town")],
            [LocationConnection(from_location="Town", to_location="Forest")]
        ))
        resp = client.post(f"/api/rpg-projects/{project_id}/locations/generate-from-story")
        assert resp.status_code == 200
        assert len(rpg_graphiti_store[project_id]["locations"]) == 1
        assert len(rpg_graphiti_store[project_id]["location_connections"]) == 1
        mock_enh.enhance_locations.assert_called_once()

    with patch("app.main.StoryLocationEnhancer") as MockEnh:
        mock_enh = MockEnh.return_value
        mock_enh.enhance_locations = AsyncMock(return_value=(
            [RPGLocation(name="Town", description="Busy")],
            [LocationConnection(from_location="Town", to_location="Forest")]
        ))
        resp = client.post(
            f"/api/rpg-projects/{project_id}/locations/Town/enhance-from-story"
        )
        assert resp.status_code == 200
        assert rpg_graphiti_store[project_id]["locations"][0].description == "Busy"
        mock_enh.enhance_locations.assert_called_once()


def test_location_connection_endpoints(client, rpg_graphiti_store):
    project_data = {"name": "ConnProj", "version": "MZ", "genre": "fantasy"}
    resp = client.post("/api/rpg-projects", json=project_data)
    project_id = resp.json()["project_id"]

    loc = {"name": "Castle"}
    resp = client.post(f"/api/rpg-projects/{project_id}/locations", json=loc)
    assert resp.status_code == 200

    conn = {"from_location": "Castle", "to_location": "Town"}
    resp = client.post(
        f"/api/rpg-projects/{project_id}/locations/Castle/connections", json=conn
    )
    assert resp.status_code == 200

    resp = client.get(
        f"/api/rpg-projects/{project_id}/locations/Castle/connections"
    )
    assert resp.status_code == 200
    assert len(resp.json()["connections"]) == 1
