import sys
import os
import types
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from game.models import RPGQuest, QuestType, QuestStatus, DialogueTree

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
graphiti_mgr_mod = types.ModuleType("core.graphiti_manager")
class GraphitiManager:
    async def initialize(self):
        pass
    async def create_rpg_project(self, *a, **k):
        pass
    async def sync_project_story(self, *a, **k):
        pass
    async def get_project_story_ids(self, *a, **k):
        return []
    async def get_project_story_content(self, *a, **k):
        return ""
    async def add_export_config(self, *a, **k):
        pass
    async def get_export_configs(self, *a, **k):
        return []
    async def add_project_variable(self, *a, **k):
        pass
    async def get_project_variables(self, *a, **k):
        return []
    async def replace_project_variables(self, *a, **k):
        pass
    async def update_project_variable(self, *a, **k):
        pass
    async def add_project_switch(self, *a, **k):
        pass
    async def get_project_switches(self, *a, **k):
        return []
    async def add_project_character(self, *a, **k):
        pass
    async def get_project_characters(self, *a, **k):
        return []
    async def replace_project_characters(self, *a, **k):
        pass
    async def update_project_character(self, *a, **k):
        pass
    async def get_character_knowledge_state(self, *a, **k):
        return []
    async def update_character_knowledge_state(self, *a, **k):
        pass
    async def add_project_location(self, *a, **k):
        pass
    async def get_project_locations(self, *a, **k):
        return []
    async def replace_project_locations(self, *a, **k):
        pass
    async def update_project_location(self, *a, **k):
        pass
    async def add_project_quest(self, *a, **k):
        pass
    async def get_project_quests(self, *a, **k):
        return []
    async def add_dialogue_tree(self, *a, **k):
        pass
    async def get_dialogue_trees(self, *a, **k):
        return []
    async def add_location_connection(self, *a, **k):
        pass
    async def replace_location_connections(self, *a, **k):
        pass
    async def get_location_connections(self, *a, **k):
        return []
graphiti_mgr_mod.GraphitiManager = GraphitiManager
sys.modules['core.graphiti_manager'] = graphiti_mgr_mod
import builtins
builtins.RPGQuest = RPGQuest
builtins.DialogueTree = DialogueTree
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


def test_quest_endpoints(client, rpg_graphiti_store):
    project_data = {"name": "QuestProj", "version": "MZ", "genre": "fantasy"}
    resp = client.post("/api/rpg-projects", json=project_data)
    project_id = resp.json()["project_id"]

    quest = {
        "name": "Retrieve Sword",
        "quest_type": "main",
        "status": "not_started",
        "description": "Find the lost sword",
        "objectives": [],
        "rewards": [],
        "prerequisites": []
    }
    resp = client.post(f"/api/rpg-projects/{project_id}/quests", json=quest)
    assert resp.status_code == 200
    assert len(rpg_graphiti_store[project_id]["quests"]) == 1

    resp = client.get(f"/api/rpg-projects/{project_id}/quests")
    assert resp.status_code == 200
    assert len(resp.json()["quests"]) == 1


def test_generate_quest_from_story(client, rpg_graphiti_store):
    project_data = {"name": "GenQuest", "version": "MZ", "genre": "fantasy"}
    resp = client.post("/api/rpg-projects", json=project_data)
    project_id = resp.json()["project_id"]

    story = {"story_id": "s1", "content": "Hero story"}
    client.post(f"/api/rpg-projects/{project_id}/sync-story", json=story)

    with patch("app.main.StoryQuestGenerator") as MockGen:
        mock_gen = MockGen.return_value
        mock_gen.generate_quest_from_story_event = AsyncMock(return_value=RPGQuest(
            name="Retrieve Sword",
            quest_type=QuestType.MAIN,
            status=QuestStatus.NOT_STARTED,
            description="Find",
            objectives=[],
            rewards=[],
            prerequisites=[]
        ))

        req = {"event_id": "e1", "story_id": "s1"}
        resp = client.post(
            f"/api/rpg-projects/{project_id}/quests/generate-from-story",
            json=req,
        )
        assert resp.status_code == 200
        assert len(rpg_graphiti_store[project_id]["quests"]) == 1
        mock_gen.generate_quest_from_story_event.assert_called_once_with("s1", "e1")
