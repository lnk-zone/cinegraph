"""Tests for the ConsistencyEngine class."""

import pytest
import asyncio
import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from graphiti.rules.consistency_engine import ConsistencyEngine, ContradictionMatch


@pytest.mark.asyncio
async def test_consistency_engine_initialization(consistency_engine):
    """Test that ConsistencyEngine initializes correctly."""
    assert consistency_engine is not None
    assert hasattr(consistency_engine, 'graphiti')
    assert hasattr(consistency_engine, 'cypher_rules')
    assert len(consistency_engine.cypher_rules) > 0


@pytest.mark.asyncio
async def test_cypher_rules_setup(consistency_engine):
    """Test that Cypher rules are properly configured."""
    expected_rules = [
        'detect_temporal_contradictions',
        'detect_relationship_contradictions',
        'detect_location_contradictions',
        'detect_character_state_contradictions',
        'find_unlinked_contradictions'
    ]
    
    for rule in expected_rules:
        assert rule in consistency_engine.cypher_rules
        assert isinstance(consistency_engine.cypher_rules[rule], str)
        assert len(consistency_engine.cypher_rules[rule]) > 0


@pytest.mark.asyncio
async def test_detect_contradictions_empty_results(consistency_engine):
    """Test detecting contradictions when no contradictions exist."""
    result = await consistency_engine.detect_contradictions("test_story", "test_user")
    
    # The method returns a ContradictionDetectionResult object, not a list
    assert hasattr(result, 'contradictions_found')
    assert len(result.contradictions_found) == 0

@pytest.mark.asyncio
async def test_create_contradiction_edges(consistency_engine):
    """Test creation of CONTRADICTS edges."""
    # Create test contradiction
    contradiction = ContradictionMatch(
        from_knowledge_id="k1",
        to_knowledge_id="k2",
        severity="medium",
        reason="Test contradiction",
        detected_at=datetime.now(),
        confidence=0.8
    )
    
    # This should not raise an exception
    await consistency_engine.create_contradiction_edges([contradiction], "test_story")


@pytest.mark.asyncio
async def test_run_consistency_scan(consistency_engine):
    """Test running a full consistency scan."""
    # This should not raise an exception
    await consistency_engine.run_consistency_scan("test_story")


@pytest.mark.asyncio
async def test_get_contradiction_report(consistency_engine):
    """Test generating a contradiction report."""
    report = await consistency_engine.get_contradiction_report()
    
    assert isinstance(report, dict)
    assert 'total_contradictions' in report
    assert 'contradictions_by_severity' in report
    assert 'severity_counts' in report
    assert 'generated_at' in report


@pytest.mark.asyncio
async def test_temporal_contradiction_query(consistency_engine):
    """Test the temporal contradiction query structure."""
    query = consistency_engine._get_temporal_contradiction_query()
    
    assert isinstance(query, str)
    assert 'MATCH' in query
    assert 'KNOWS' in query
    assert 'Knowledge' in query
    assert 'CONTRADICTS' in query
    assert 'NOT EXISTS' in query


@pytest.mark.asyncio
async def test_relationship_contradiction_query(consistency_engine):
    """Test the relationship contradiction query structure."""
    query = consistency_engine._get_relationship_contradiction_query()
    
    assert isinstance(query, str)
    assert 'MATCH' in query
    assert 'RELATIONSHIP' in query
    assert 'Character' in query
    assert 'relationship_type' in query


@pytest.mark.asyncio
async def test_location_contradiction_query(consistency_engine):
    """Test the location contradiction query structure."""
    query = consistency_engine._get_location_contradiction_query()
    
    assert isinstance(query, str)
    assert 'MATCH' in query
    assert 'PRESENT_IN' in query
    assert 'OCCURS_IN' in query
    assert 'Location' in query
    assert 'scene_order' in query


@pytest.mark.asyncio
async def test_character_state_contradiction_query(consistency_engine):
    """Test the character state contradiction query structure."""
    query = consistency_engine._get_character_state_contradiction_query()
    
    assert isinstance(query, str)
    assert 'MATCH' in query
    assert 'KNOWS' in query
    assert 'dead' in query
    assert 'alive' in query
    assert 'duration.between' in query


@pytest.mark.asyncio
async def test_unlinked_contradictions_query(consistency_engine):
    """Test the unlinked contradictions query structure."""
    query = consistency_engine._get_unlinked_contradictions_query()
    
    assert isinstance(query, str)
    assert 'MATCH' in query
    assert 'Knowledge' in query
    assert 'NOT EXISTS' in query
    assert 'CONTRADICTS' in query
    assert 'CONTAINS' in query
