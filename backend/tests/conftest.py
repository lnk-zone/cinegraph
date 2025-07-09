"""Test configuration and fixtures for Graphiti rules testing."""

import os
import pytest
import asyncio
import pytest_asyncio
from graphiti.rules.validation_rules import ValidationRules
from graphiti.rules.background_jobs import BackgroundConsistencyJob
from graphiti.rules.consistency_engine import ConsistencyEngine


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

