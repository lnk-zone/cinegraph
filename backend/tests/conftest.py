"""Test configuration and fixtures for Graphiti rules testing."""

import os
import sys
import pytest
import asyncio
import pytest_asyncio

# Add the parent directory to the path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from graphiti_core import Graphiti
    from graphiti.rules.validation_rules import ValidationRules
    from graphiti.rules.background_jobs import BackgroundConsistencyJob
    from graphiti.rules.consistency_engine import ConsistencyEngine
except ModuleNotFoundError:
    class Graphiti:
        async def build_indices_and_constraints(self):
            pass

    class ValidationRules:
        def __init__(self, graphiti):
            pass

    class BackgroundConsistencyJob:
        def __init__(self, graphiti):
            pass

    class ConsistencyEngine:
        def __init__(self, graphiti):
            pass


class MockGraphiti:
    """Mock Graphiti instance for testing."""
    
    async def initialize(self):
        pass
    
    async def close(self):
        pass
    
    async def register_trigger(self, trigger_name, trigger_type, callback):
        pass
    
    async def execute_cypher(self, query):
        return []
    
    async def create_edge(self, edge_type, from_id, to_id, properties):
        pass


@pytest_asyncio.fixture
async def graphiti_instance():
    """Create a mock Graphiti instance for testing."""
    graphiti = MockGraphiti()
    await graphiti.initialize()
    yield graphiti
    await graphiti.close()


@pytest_asyncio.fixture
async def validation_rules(graphiti_instance):
    """Create ValidationRules instance for testing."""
    return ValidationRules(graphiti_instance)


@pytest_asyncio.fixture
async def consistency_engine(graphiti_instance):
    """Create ConsistencyEngine instance for testing."""
    return ConsistencyEngine(graphiti_instance)


@pytest_asyncio.fixture
async def background_job(graphiti_instance):
    """Create BackgroundConsistencyJob instance for testing."""
    return BackgroundConsistencyJob(graphiti_instance)


@pytest.fixture(autouse=True)
def rpg_graphiti_store(monkeypatch):
    """Mock GraphitiManager for RPG endpoint tests."""
    from app.main import graphiti_manager
    store = {}

    async def create_rpg_project(project):
        pid = f"proj_{len(store)+1}"
        store[pid] = {
            "project": project,
            "stories": {},
            "export_configs": [],
            "variables": [],
            "switches": [],
            "characters": [],
            "locations": [],
            "location_connections": [],
        }
        return pid

    async def sync_project_story(pid, story):
        store[pid]["stories"][story.story_id] = story.content

    async def get_project_story_ids(pid):
        return list(store.get(pid, {}).get("stories", {}).keys())

    async def get_project_story_content(pid, sid):
        return store[pid]["stories"][sid]

    async def add_export_config(pid, cfg):
        store[pid]["export_configs"].append(cfg)

    async def get_export_configs(pid):
        return store[pid]["export_configs"]

    async def add_project_variable(pid, var):
        store[pid]["variables"].append(var)

    async def get_project_variables(pid):
        return store[pid]["variables"]

    async def replace_project_variables(pid, vars):
        store[pid]["variables"] = list(vars)

    async def update_project_variable(pid, var):
        for idx, v in enumerate(store[pid]["variables"]):
            if v.name == var.name:
                store[pid]["variables"][idx] = var

    async def add_project_switch(pid, sw):
        store[pid]["switches"].append(sw)

    async def get_project_switches(pid):
        return store[pid]["switches"]

    async def add_project_character(pid, char):
        store[pid]["characters"].append(char)

    async def get_project_characters(pid):
        return store[pid]["characters"]

    async def replace_project_characters(pid, chars):
        store[pid]["characters"] = list(chars)

    async def update_project_character(pid, char):
        for idx, c in enumerate(store[pid]["characters"]):
            if c.name == char.name:
                store[pid]["characters"][idx] = char

    async def get_character_knowledge_state(pid, cid):
        for c in store[pid]["characters"]:
            if c.name == cid:
                return c.knowledge_state
        return []

    async def update_character_knowledge_state(pid, cid, knowledge):
        for c in store[pid]["characters"]:
            if c.name == cid:
                c.knowledge_state = knowledge

    async def add_project_location(pid, loc):
        store[pid]["locations"].append(loc)

    async def get_project_locations(pid):
        return store[pid]["locations"]

    async def replace_project_locations(pid, locs):
        store[pid]["locations"] = list(locs)

    async def update_project_location(pid, loc):
        for idx, l in enumerate(store[pid]["locations"]):
            if l.name == loc.name:
                store[pid]["locations"][idx] = loc

    async def add_location_connection(pid, conn):
        store[pid]["location_connections"].append(conn)

    async def replace_location_connections(pid, conns):
        store[pid]["location_connections"] = list(conns)

    async def get_location_connections(pid, lid):
        return [c for c in store[pid]["location_connections"] if c.from_location == lid or c.to_location == lid]

    monkeypatch.setattr(graphiti_manager, "create_rpg_project", create_rpg_project)
    monkeypatch.setattr(graphiti_manager, "sync_project_story", sync_project_story)
    monkeypatch.setattr(graphiti_manager, "get_project_story_ids", get_project_story_ids)
    monkeypatch.setattr(graphiti_manager, "get_project_story_content", get_project_story_content)
    monkeypatch.setattr(graphiti_manager, "add_export_config", add_export_config)
    monkeypatch.setattr(graphiti_manager, "get_export_configs", get_export_configs)
    monkeypatch.setattr(graphiti_manager, "add_project_variable", add_project_variable)
    monkeypatch.setattr(graphiti_manager, "get_project_variables", get_project_variables)
    monkeypatch.setattr(graphiti_manager, "replace_project_variables", replace_project_variables)
    monkeypatch.setattr(graphiti_manager, "update_project_variable", update_project_variable)
    monkeypatch.setattr(graphiti_manager, "add_project_switch", add_project_switch)
    monkeypatch.setattr(graphiti_manager, "get_project_switches", get_project_switches)
    monkeypatch.setattr(graphiti_manager, "add_project_character", add_project_character)
    monkeypatch.setattr(graphiti_manager, "get_project_characters", get_project_characters)
    monkeypatch.setattr(graphiti_manager, "replace_project_characters", replace_project_characters)
    monkeypatch.setattr(graphiti_manager, "update_project_character", update_project_character)
    monkeypatch.setattr(graphiti_manager, "get_character_knowledge_state", get_character_knowledge_state)
    monkeypatch.setattr(graphiti_manager, "update_character_knowledge_state", update_character_knowledge_state)
    monkeypatch.setattr(graphiti_manager, "add_project_location", add_project_location)
    monkeypatch.setattr(graphiti_manager, "get_project_locations", get_project_locations)
    monkeypatch.setattr(graphiti_manager, "replace_project_locations", replace_project_locations)
    monkeypatch.setattr(graphiti_manager, "update_project_location", update_project_location)
    monkeypatch.setattr(graphiti_manager, "add_location_connection", add_location_connection)
    monkeypatch.setattr(graphiti_manager, "replace_location_connections", replace_location_connections)
    monkeypatch.setattr(graphiti_manager, "get_location_connections", get_location_connections)

    yield store

