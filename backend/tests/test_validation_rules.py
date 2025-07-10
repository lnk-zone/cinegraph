"""Comprehensive tests for ValidationRules class."""

import pytest
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from graphiti.rules.validation_rules import ValidationRules, ValidationError


@pytest.mark.asyncio
async def test_validation_rules_initialization(validation_rules):
    """Test that ValidationRules initializes correctly."""
    assert validation_rules is not None
    assert hasattr(validation_rules, 'graphiti')
    assert hasattr(validation_rules, 'rules')
    assert len(validation_rules.rules) > 0


@pytest.mark.asyncio
async def test_prevent_invalid_knows_edges_failure(validation_rules):
    """
    Test "prevent_invalid_knows_edges" to ensure it blocks KNOWS edges with invalid timestamps.
    """
    from_node = {
        'character_id': '1',
        'name': 'Alice',
        'created_at': '2023-01-10T10:00:00'
    }

    to_node = {
        'knowledge_id': '101',
        'content': 'Secret',
        'valid_from': '2023-01-05T10:00:00'
    }

    edge_properties = {}

    is_valid, error_msg = await validation_rules._prevent_invalid_knows_edges(
        "KNOWS",
        from_node,
        to_node,
        edge_properties
    )

    assert not is_valid, "Expected failure for invalid KNOWS edge"
    assert "Knowledge valid from" in error_msg


@pytest.mark.asyncio
async def test_prevent_invalid_knows_edges_success(validation_rules):
    """
    Test "prevent_invalid_knows_edges" allows valid KNOWS edges.
    """
    from_node = {
        'character_id': '1',
        'name': 'Alice',
        'created_at': '2023-01-05T10:00:00'
    }

    to_node = {
        'knowledge_id': '101',
        'content': 'Secret',
        'valid_from': '2023-01-10T10:00:00'
    }

    edge_properties = {}

    is_valid, error_msg = await validation_rules._prevent_invalid_knows_edges(
        "KNOWS",
        from_node,
        to_node,
        edge_properties
    )

    assert is_valid, "Expected success for valid KNOWS edge"
    assert error_msg == ""


@pytest.mark.asyncio
async def test_prevent_invalid_knows_edges_non_knows_edge(validation_rules):
    """
    Test "prevent_invalid_knows_edges" ignores non-KNOWS edges.
    """
    from_node = {'character_id': '1'}
    to_node = {'knowledge_id': '101'}
    edge_properties = {}

    is_valid, error_msg = await validation_rules._prevent_invalid_knows_edges(
        "RELATIONSHIP",
        from_node,
        to_node,
        edge_properties
    )

    assert is_valid, "Expected success for non-KNOWS edge"
    assert error_msg == ""


@pytest.mark.asyncio
async def test_prevent_relationship_self_loops_failure(validation_rules):
    """
    Test "prevent_relationship_self_loops" to ensure it blocks RELATIONSHIP self-loops.
    """
    from_node = {
        'character_id': '1',
        'name': 'Alice'
    }

    to_node = {
        'character_id': '1',
        'name': 'Alice'
    }

    edge_properties = {}

    is_valid, error_msg = await validation_rules._prevent_relationship_self_loops(
        "RELATIONSHIP",
        from_node,
        to_node,
        edge_properties
    )

    assert not is_valid, "Expected failure for RELATIONSHIP self-loop"
    assert "Self-loop detected" in error_msg


@pytest.mark.asyncio
async def test_prevent_relationship_self_loops_success(validation_rules):
    """
    Test "prevent_relationship_self_loops" allows valid relationships.
    """
    from_node = {
        'character_id': '1',
        'name': 'Alice'
    }

    to_node = {
        'character_id': '2',
        'name': 'Bob'
    }

    edge_properties = {}

    is_valid, error_msg = await validation_rules._prevent_relationship_self_loops(
        "RELATIONSHIP",
        from_node,
        to_node,
        edge_properties
    )

    assert is_valid, "Expected success for valid RELATIONSHIP edge"
    assert error_msg == ""


@pytest.mark.asyncio
async def test_prevent_relationship_self_loops_non_relationship_edge(validation_rules):
    """
    Test "prevent_relationship_self_loops" ignores non-RELATIONSHIP edges.
    """
    from_node = {'character_id': '1'}
    to_node = {'character_id': '1'}
    edge_properties = {}

    is_valid, error_msg = await validation_rules._prevent_relationship_self_loops(
        "KNOWS",
        from_node,
        to_node,
        edge_properties
    )

    assert is_valid, "Expected success for non-RELATIONSHIP edge"
    assert error_msg == ""


@pytest.mark.asyncio
async def test_validate_temporal_consistency_success(validation_rules):
    """
    Test temporal consistency validation for valid timestamps.
    """
    from_node = {}
    to_node = {}
    edge_properties = {
        'created_at': '2023-01-10T10:00:00',
        'updated_at': '2023-01-10T11:00:00'
    }

    is_valid, error_msg = await validation_rules._validate_temporal_consistency(
        "KNOWS",
        from_node,
        to_node,
        edge_properties
    )

    assert is_valid, "Expected success for valid temporal order"
    assert error_msg == ""


@pytest.mark.asyncio
async def test_validate_temporal_consistency_failure(validation_rules):
    """
    Test temporal consistency validation for invalid timestamps.
    """
    from_node = {}
    to_node = {}
    edge_properties = {
        'created_at': '2023-01-10T11:00:00',
        'updated_at': '2023-01-10T10:00:00'
    }

    is_valid, error_msg = await validation_rules._validate_temporal_consistency(
        "KNOWS",
        from_node,
        to_node,
        edge_properties
    )

    assert not is_valid, "Expected failure for invalid temporal order"
    assert "created_at cannot be after updated_at" in error_msg


@pytest.mark.asyncio
async def test_validate_scene_order_success(validation_rules):
    """
    Test scene order validation for valid scene order.
    """
    from_node = {'character_id': '1'}
    to_node = {'scene_id': '1', 'scene_order': 1}
    edge_properties = {}

    is_valid, error_msg = await validation_rules._validate_scene_order(
        "PRESENT_IN",
        from_node,
        to_node,
        edge_properties
    )

    assert is_valid, "Expected success for valid scene order"
    assert error_msg == ""


@pytest.mark.asyncio
async def test_validate_scene_order_failure(validation_rules):
    """
    Test scene order validation for invalid scene order.
    """
    from_node = {'character_id': '1'}
    to_node = {'scene_id': '1', 'scene_order': -1}
    edge_properties = {}

    is_valid, error_msg = await validation_rules._validate_scene_order(
        "PRESENT_IN",
        from_node,
        to_node,
        edge_properties
    )

    assert not is_valid, "Expected failure for negative scene order"
    assert "Scene order must be non-negative" in error_msg


@pytest.mark.asyncio
async def test_validate_edge_creation_success(validation_rules):
    """
    Test the main validate_edge_creation method for valid edge.
    """
    from_node = {
        'character_id': '1',
        'name': 'Alice'
    }

    to_node = {
        'character_id': '2',
        'name': 'Bob'
    }

    edge_properties = {
        'created_at': '2023-01-10T10:00:00',
        'updated_at': '2023-01-10T11:00:00'
    }

    is_valid, error_msg = await validation_rules.validate_edge_creation(
        "RELATIONSHIP",
        from_node,
        to_node,
        edge_properties
    )

    assert is_valid, "Expected success for valid edge"
    assert error_msg == ""


@pytest.mark.asyncio
async def test_validate_edge_creation_failure(validation_rules):
    """
    Test the main validate_edge_creation method for invalid edge.
    """
    from_node = {
        'character_id': '1',
        'name': 'Alice'
    }

    to_node = {
        'character_id': '1',
        'name': 'Alice'
    }

    edge_properties = {}

    is_valid, error_msg = await validation_rules.validate_edge_creation(
        "RELATIONSHIP",
        from_node,
        to_node,
        edge_properties
    )

    assert not is_valid, "Expected failure for self-loop"
    assert "prevent_relationship_self_loops" in error_msg


@pytest.mark.asyncio
async def test_register_triggers(validation_rules):
    """
    Test registering validation triggers.
    """
    # This should not raise an exception
    await validation_rules.register_triggers()


@pytest.mark.asyncio
async def test_get_validation_stats(validation_rules):
    """
    Test getting validation statistics.
    """
    stats = await validation_rules.get_validation_stats()
    
    assert isinstance(stats, dict)
    assert 'total_validations' in stats
    assert 'failed_validations' in stats
    assert 'rules_enabled' in stats
    assert 'active_triggers' in stats
    
    assert stats['rules_enabled'] == len(validation_rules.rules)
    assert 'edge_validation' in stats['active_triggers']


@pytest.mark.asyncio
async def test_validation_error_exception():
    """
    Test ValidationError exception.
    """
    error = ValidationError("test_rule", "test message")
    
    assert error.rule_name == "test_rule"
    assert error.message == "test message"
    assert "Validation rule 'test_rule' failed: test message" in str(error)

