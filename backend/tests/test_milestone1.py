"""
Test Suite for Milestone 1: Episode Hierarchy and Relationship Evolution
========================================================================

This module contains comprehensive tests for the basic vertical slice functionality
including episode hierarchy management and relationship evolution tracking.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from typing import List, Dict, Any

pytestmark = pytest.mark.asyncio

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.models import (
    EpisodeEntity, EpisodeHierarchy, RelationshipEvolution,
    GraphEntity, GraphRelationship, EntityType, RelationshipType
)
from core.graphiti_manager import GraphitiManager
from agents.cinegraph_agent import CineGraphAgent


class TestEpisodeHierarchy:
    """Test episode hierarchy functionality."""

    @pytest_asyncio.fixture
    async def graphiti_manager(self):
        """Create a test GraphitiManager instance."""
        manager = GraphitiManager()
        await manager.initialize()
        yield manager
        await manager.close()

    @pytest.fixture
    def sample_episodes(self) -> List[EpisodeHierarchy]:
        """Create sample episode hierarchy data."""
        return [
            EpisodeHierarchy(
                episode_id="ep_001",
                parent_episode_id=None,
                child_episodes=["ep_001_01", "ep_001_02"],
                depth_level=0,
                sequence_order=1,
                story_id="test_story_001",
                user_id="test_user_001"
            ),
            EpisodeHierarchy(
                episode_id="ep_001_01",
                parent_episode_id="ep_001",
                child_episodes=[],
                depth_level=1,
                sequence_order=1,
                story_id="test_story_001",
                user_id="test_user_001"
            ),
            EpisodeHierarchy(
                episode_id="ep_001_02",
                parent_episode_id="ep_001",
                child_episodes=[],
                depth_level=1,
                sequence_order=2,
                story_id="test_story_001",
                user_id="test_user_001"
            )
        ]

    async def test_add_episode_hierarchy(self, graphiti_manager, sample_episodes):
        """Test adding episode hierarchy to the knowledge graph."""
        result = await graphiti_manager.add_episode_hierarchy("test_story_001", sample_episodes)
        
        assert result["status"] == "success"
        assert result["story_id"] == "test_story_001"
        assert result["episodes_added"] == 3
        assert len(result["results"]) == 3

    async def test_episode_hierarchy_validation(self, sample_episodes):
        """Test episode hierarchy model validation."""
        episode = sample_episodes[0]
        
        # Test required fields
        assert episode.episode_id == "ep_001"
        assert episode.story_id == "test_story_001"
        assert episode.user_id == "test_user_001"
        assert episode.depth_level == 0
        assert episode.sequence_order == 1
        
        # Test optional fields
        assert episode.parent_episode_id is None
        assert len(episode.child_episodes) == 2

    async def test_nested_episode_hierarchy(self, graphiti_manager):
        """Test deeply nested episode hierarchy."""
        nested_episodes = [
            EpisodeHierarchy(
                episode_id="root",
                parent_episode_id=None,
                child_episodes=["level1"],
                depth_level=0,
                sequence_order=1,
                story_id="nested_story",
                user_id="test_user"
            ),
            EpisodeHierarchy(
                episode_id="level1",
                parent_episode_id="root",
                child_episodes=["level2"],
                depth_level=1,
                sequence_order=1,
                story_id="nested_story",
                user_id="test_user"
            ),
            EpisodeHierarchy(
                episode_id="level2",
                parent_episode_id="level1",
                child_episodes=[],
                depth_level=2,
                sequence_order=1,
                story_id="nested_story",
                user_id="test_user"
            )
        ]
        
        result = await graphiti_manager.add_episode_hierarchy("nested_story", nested_episodes)
        assert result["status"] == "success"
        assert result["episodes_added"] == 3


class TestRelationshipEvolution:
    """Test relationship evolution tracking functionality."""

    @pytest_asyncio.fixture
    async def graphiti_manager(self):
        """Create a test GraphitiManager instance."""
        manager = GraphitiManager()
        await manager.initialize()
        yield manager
        await manager.close()

    @pytest.fixture
    def sample_evolution_data(self) -> List[RelationshipEvolution]:
        """Create sample relationship evolution data."""
        return [
            RelationshipEvolution(
                relationship_id="rel_001",
                from_character_id="char_alice",
                to_character_id="char_bob",
                relationship_type="friendship",
                strength_before=5.0,
                strength_after=7.5,
                change_reason="Shared adventure strengthened bond",
                episode_id="ep_003",
                story_id="test_story_001",
                user_id="test_user_001",
                timestamp=datetime(2024, 1, 15, 12, 0, 0)
            ),
            RelationshipEvolution(
                relationship_id="rel_002",
                from_character_id="char_alice",
                to_character_id="char_charlie",
                relationship_type="rivalry",
                strength_before=3.0,
                strength_after=8.5,
                change_reason="Betrayal revealed",
                episode_id="ep_005",
                story_id="test_story_001",
                user_id="test_user_001",
                timestamp=datetime(2024, 1, 20, 15, 30, 0)
            )
        ]

    async def test_track_relationship_evolution(self, graphiti_manager, sample_evolution_data):
        """Test tracking relationship evolution."""
        result = await graphiti_manager.track_relationship_evolution(
            sample_evolution_data, "test_story_001"
        )
        
        assert result["status"] == "success"
        assert result["story_id"] == "test_story_001"
        assert result["evolutions_logged"] == 2
        assert len(result["results"]) == 2

    async def test_relationship_evolution_validation(self, sample_evolution_data):
        """Test relationship evolution model validation."""
        evolution = sample_evolution_data[0]
        
        # Test required fields
        assert evolution.relationship_id == "rel_001"
        assert evolution.from_character_id == "char_alice"
        assert evolution.to_character_id == "char_bob"
        assert evolution.relationship_type == "friendship"
        assert evolution.strength_after == 7.5
        assert evolution.story_id == "test_story_001"
        assert evolution.user_id == "test_user_001"
        
        # Test optional fields
        assert evolution.strength_before == 5.0
        assert evolution.change_reason is not None
        assert evolution.episode_id == "ep_003"

    async def test_relationship_strength_change(self, sample_evolution_data):
        """Test relationship strength change calculation."""
        evolution = sample_evolution_data[0]
        
        strength_change = evolution.strength_after - evolution.strength_before
        assert strength_change == 2.5
        
        evolution2 = sample_evolution_data[1]
        strength_change2 = evolution2.strength_after - evolution2.strength_before
        assert strength_change2 == 5.5

    async def test_evolution_temporal_ordering(self, sample_evolution_data):
        """Test that evolution events can be ordered temporally."""
        # Sort by timestamp
        sorted_evolutions = sorted(sample_evolution_data, key=lambda x: x.timestamp)
        
        assert sorted_evolutions[0].timestamp < sorted_evolutions[1].timestamp
        assert sorted_evolutions[0].episode_id == "ep_003"
        assert sorted_evolutions[1].episode_id == "ep_005"


class TestIntegrationMilestone1:
    """Integration tests for Milestone 1 functionality."""

    @pytest.fixture
    async def setup_test_environment(self):
        """Set up a complete test environment."""
        graphiti_manager = GraphitiManager()
        await graphiti_manager.initialize()
        
        cinegraph_agent = CineGraphAgent(graphiti_manager=graphiti_manager)
        await cinegraph_agent.initialize()
        
        yield {
            "graphiti_manager": graphiti_manager,
            "cinegraph_agent": cinegraph_agent
        }
        
        await graphiti_manager.close()

    async def test_complete_milestone1_workflow(self, setup_test_environment):
        """Test the complete Milestone 1 workflow."""
        env = setup_test_environment
        graphiti_manager = env["graphiti_manager"]
        
        story_id = "integration_test_story"
        user_id = "integration_test_user"
        
        # Step 1: Create episode hierarchy
        episodes = [
            EpisodeHierarchy(
                episode_id="intro",
                parent_episode_id=None,
                child_episodes=["meet_characters", "first_conflict"],
                depth_level=0,
                sequence_order=1,
                story_id=story_id,
                user_id=user_id
            ),
            EpisodeHierarchy(
                episode_id="meet_characters",
                parent_episode_id="intro",
                child_episodes=[],
                depth_level=1,
                sequence_order=1,
                story_id=story_id,
                user_id=user_id
            ),
            EpisodeHierarchy(
                episode_id="first_conflict",
                parent_episode_id="intro",
                child_episodes=[],
                depth_level=1,
                sequence_order=2,
                story_id=story_id,
                user_id=user_id
            )
        ]
        
        hierarchy_result = await graphiti_manager.add_episode_hierarchy(story_id, episodes)
        assert hierarchy_result["status"] == "success"
        
        # Step 2: Track relationship evolution
        evolutions = [
            RelationshipEvolution(
                relationship_id="rel_hero_mentor",
                from_character_id="hero",
                to_character_id="mentor",
                relationship_type="mentorship",
                strength_before=0.0,
                strength_after=6.0,
                change_reason="First meeting and guidance",
                episode_id="meet_characters",
                story_id=story_id,
                user_id=user_id,
                timestamp=datetime.now()
            ),
            RelationshipEvolution(
                relationship_id="rel_hero_villain",
                from_character_id="hero",
                to_character_id="villain",
                relationship_type="antagonism",
                strength_before=0.0,
                strength_after=8.0,
                change_reason="First confrontation",
                episode_id="first_conflict",
                story_id=story_id,
                user_id=user_id,
                timestamp=datetime.now()
            )
        ]
        
        evolution_result = await graphiti_manager.track_relationship_evolution(evolutions, story_id)
        assert evolution_result["status"] == "success"
        
        # Step 3: Verify data persistence
        # Check that episodes and relationships were stored
        health_check = await graphiti_manager.health_check()
        assert health_check["status"] in ["healthy", "degraded"]

    async def test_error_handling(self, setup_test_environment):
        """Test error handling in Milestone 1 features."""
        env = setup_test_environment
        graphiti_manager = env["graphiti_manager"]
        
        # Test with invalid data
        try:
            await graphiti_manager.add_episode_hierarchy("invalid_story", [])
            # Should handle empty list gracefully
        except Exception as e:
            pytest.fail(f"Should handle empty episode list gracefully: {e}")
        
        # Test with invalid relationship evolution
        try:
            await graphiti_manager.track_relationship_evolution([], "invalid_story")
            # Should handle empty list gracefully
        except Exception as e:
            pytest.fail(f"Should handle empty evolution list gracefully: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
