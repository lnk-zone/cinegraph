#!/usr/bin/env python3
"""
Comprehensive Tests for Episodic Refactor - Step 7
==================================================

This test suite covers:
1. Adjusting existing tests that expected Cypher results
2. Testing episodic health check returns healthy
3. Testing stats call works with zero/one/many sessions
4. Testing `_run_cypher_query` is gated by env var
5. Comprehensive regression testing
"""

import pytest
import pytest_asyncio
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, List, Any

# Import the modules we're testing
from core.graphiti_manager import GraphitiManager
from core.models import GraphitiConfig
from agents.cinegraph_agent import CineGraphAgent
from app.main import app


class TestEpisodicHealthCheck:
    """Test episodic health check functionality."""
    
    @pytest_asyncio.fixture
    async def graphiti_manager(self):
        """Create a GraphitiManager instance for testing."""
        config = GraphitiConfig(
            database_url="bolt://localhost:7687",
            username="neo4j",
            password="password",
            database_name="neo4j"
        )
        manager = GraphitiManager(config)
        
        # Mock the client to avoid real database connections
        manager.client = Mock()
        manager.client.search = AsyncMock(return_value=[{"test": "data"}])
        
        yield manager
        
        if manager.client:
            await manager.close()
    
    @pytest.mark.asyncio
    async def test_episodic_health_check_returns_healthy(self, graphiti_manager):
        """Test that episodic health check returns healthy status."""
        # Arrange
        graphiti_manager.client.search = AsyncMock(return_value=[{"test": "data"}])
        
        # Act
        health_result = await graphiti_manager.health_check()
        
        # Assert
        assert health_result["status"] == "healthy"
        assert health_result["connectivity_confirmed"] is True
        assert health_result["search_result_count"] == 1
        assert "episodic API" in health_result["note"]
        
        # Verify search was called with correct parameters
        graphiti_manager.client.search.assert_called_once_with(
            query='*', 
            group_ids=None, 
            num_results=1
        )
    
    @pytest.mark.asyncio
    async def test_episodic_health_check_degraded_when_search_fails(self, graphiti_manager):
        """Test that health check returns degraded when search fails."""
        # Arrange
        graphiti_manager.client.search = AsyncMock(side_effect=Exception("Search failed"))
        
        # Act
        health_result = await graphiti_manager.health_check()
        
        # Assert
        assert health_result["status"] == "degraded"
        assert health_result["connectivity_confirmed"] is False
        assert health_result["search_result_count"] == "unknown"
    
    @pytest.mark.asyncio
    async def test_episodic_health_check_no_client(self):
        """Test health check when no client is connected."""
        # Arrange
        manager = GraphitiManager()
        manager.client = None
        
        # Act
        health_result = await manager.health_check()
        
        # Assert
        assert health_result["status"] == "disconnected"
        assert "No client connection" in health_result["error"]
    
    @pytest.mark.asyncio
    async def test_episodic_health_check_never_raises_exception(self, graphiti_manager):
        """Test that health check never raises exceptions, always returns status."""
        # Arrange
        graphiti_manager.client = None
        graphiti_manager.config = None  # This should cause an error but still return status
        
        # Act & Assert - should not raise
        health_result = await graphiti_manager.health_check()
        assert health_result["status"] == "disconnected"  # No client means disconnected
        assert "error" in health_result


class TestSessionStatsTracking:
    """Test stats calls work with zero/one/many sessions."""
    
    @pytest_asyncio.fixture
    async def graphiti_manager(self):
        """Create a GraphitiManager instance for testing."""
        config = GraphitiConfig(
            database_url="bolt://localhost:7687",
            username="neo4j",
            password="password",
            database_name="neo4j"
        )
        manager = GraphitiManager(config)
        manager.client = Mock()
        yield manager
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_stats_with_zero_sessions(self, graphiti_manager):
        """Test stats call works with zero active sessions."""
        # Arrange - ensure no sessions are tracked
        graphiti_manager._story_sessions = {}
        
        # Act
        active_stories = await graphiti_manager.get_active_stories()
        
        # Assert
        assert isinstance(active_stories, list)
        assert len(active_stories) == 0
    
    @pytest.mark.asyncio
    async def test_stats_with_one_session(self, graphiti_manager):
        """Test stats call works with one active session."""
        # Arrange
        graphiti_manager._story_sessions = {"story_1": "session_123"}
        
        # Act
        active_stories = await graphiti_manager.get_active_stories()
        
        # Assert
        assert isinstance(active_stories, list)
        assert len(active_stories) == 1
        assert "story_1" in active_stories
    
    @pytest.mark.asyncio
    async def test_stats_with_many_sessions(self, graphiti_manager):
        """Test stats call works with many active sessions."""
        # Arrange
        graphiti_manager._story_sessions = {
            "story_1": "session_123",
            "story_2": "session_456", 
            "story_3": "session_789",
            "story_4": "session_abc",
            "story_5": "session_def"
        }
        
        # Act
        active_stories = await graphiti_manager.get_active_stories()
        
        # Assert
        assert isinstance(active_stories, list)
        assert len(active_stories) == 5
        assert all(story_id in active_stories for story_id in [
            "story_1", "story_2", "story_3", "story_4", "story_5"
        ])
    
    @pytest.mark.asyncio
    async def test_stats_call_handles_exceptions_gracefully(self, graphiti_manager):
        """Test that stats calls handle exceptions gracefully."""
        # Arrange
        graphiti_manager.client = None  # This should trigger the error handling
        
        # Act & Assert - should raise RuntimeError for no client
        with pytest.raises(RuntimeError, match="Client not connected"):
            await graphiti_manager.get_active_stories()


class TestCypherQueryGating:
    """Test that _run_cypher_query is properly gated by environment variable."""
    
    @pytest_asyncio.fixture
    async def graphiti_manager(self):
        """Create a GraphitiManager instance for testing."""
        config = GraphitiConfig(
            database_url="bolt://localhost:7687",
            username="neo4j",
            password="password",
            database_name="neo4j"
        )
        manager = GraphitiManager(config)
        manager.client = Mock()
        manager.client.get_nodes_by_query = AsyncMock(return_value=[{"result": "test"}])
        yield manager
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_cypher_query_disabled_by_default(self, graphiti_manager):
        """Test that Cypher queries are disabled by default."""
        # Arrange
        # Ensure environment variable is not set
        if "GRAPHITI_ALLOW_CYPHER" in os.environ:
            del os.environ["GRAPHITI_ALLOW_CYPHER"]
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Direct Cypher queries are disabled"):
            await graphiti_manager._run_cypher_query("MATCH (n) RETURN n")
    
    @pytest.mark.asyncio
    async def test_cypher_query_disabled_when_env_false(self, graphiti_manager):
        """Test that Cypher queries are disabled when env var is false."""
        # Arrange
        os.environ["GRAPHITI_ALLOW_CYPHER"] = "false"
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Direct Cypher queries are disabled"):
            await graphiti_manager._run_cypher_query("MATCH (n) RETURN n")
        
        # Cleanup
        del os.environ["GRAPHITI_ALLOW_CYPHER"]
    
    @pytest.mark.asyncio
    async def test_cypher_query_disabled_when_env_invalid(self, graphiti_manager):
        """Test that Cypher queries are disabled when env var has invalid value."""
        # Arrange
        os.environ["GRAPHITI_ALLOW_CYPHER"] = "maybe"
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Direct Cypher queries are disabled"):
            await graphiti_manager._run_cypher_query("MATCH (n) RETURN n")
        
        # Cleanup
        del os.environ["GRAPHITI_ALLOW_CYPHER"]
    
    @pytest.mark.asyncio
    async def test_cypher_query_enabled_when_env_true(self, graphiti_manager):
        """Test that Cypher queries are enabled when env var is true."""
        # Arrange
        os.environ["GRAPHITI_ALLOW_CYPHER"] = "true"
        
        # Act
        result = await graphiti_manager._run_cypher_query("MATCH (n) RETURN n LIMIT 1")
        
        # Assert
        assert result == [{"result": "test"}]
        graphiti_manager.client.get_nodes_by_query.assert_called_once_with("MATCH (n) RETURN n LIMIT 1")
        
        # Cleanup
        del os.environ["GRAPHITI_ALLOW_CYPHER"]
    
    @pytest.mark.asyncio
    async def test_cypher_query_enabled_case_insensitive(self, graphiti_manager):
        """Test that Cypher queries work with case insensitive 'TRUE'."""
        # Arrange
        os.environ["GRAPHITI_ALLOW_CYPHER"] = "TRUE"
        
        # Act
        result = await graphiti_manager._run_cypher_query("MATCH (n) RETURN n LIMIT 1")
        
        # Assert
        assert result == [{"result": "test"}]
        
        # Cleanup
        del os.environ["GRAPHITI_ALLOW_CYPHER"]
    
    @pytest.mark.asyncio
    async def test_cypher_query_validates_empty_query(self, graphiti_manager):
        """Test that empty Cypher queries are rejected."""
        # Arrange
        os.environ["GRAPHITI_ALLOW_CYPHER"] = "true"
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cypher query cannot be empty"):
            await graphiti_manager._run_cypher_query("")
        
        with pytest.raises(ValueError, match="Cypher query cannot be empty"):
            await graphiti_manager._run_cypher_query("   ")
        
        # Cleanup
        del os.environ["GRAPHITI_ALLOW_CYPHER"]
    
    @pytest.mark.asyncio
    async def test_cypher_query_requires_client_connection(self, graphiti_manager):
        """Test that Cypher queries require client connection."""
        # Arrange
        os.environ["GRAPHITI_ALLOW_CYPHER"] = "true"
        graphiti_manager.client = None
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Client not connected"):
            await graphiti_manager._run_cypher_query("MATCH (n) RETURN n")
        
        # Cleanup
        del os.environ["GRAPHITI_ALLOW_CYPHER"]
    
    @pytest.mark.asyncio
    async def test_cypher_query_handles_execution_errors(self, graphiti_manager):
        """Test that Cypher query execution errors are properly handled."""
        # Arrange
        os.environ["GRAPHITI_ALLOW_CYPHER"] = "true"
        graphiti_manager.client.get_nodes_by_query = AsyncMock(side_effect=Exception("Database error"))
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Cypher query execution failed"):
            await graphiti_manager._run_cypher_query("INVALID QUERY")
        
        # Cleanup
        del os.environ["GRAPHITI_ALLOW_CYPHER"]
    
    @pytest.mark.asyncio
    async def test_cypher_query_logs_warning_on_usage(self, graphiti_manager):
        """Test that Cypher query usage is logged with warning."""
        # Arrange
        os.environ["GRAPHITI_ALLOW_CYPHER"] = "true"
        
        with patch('logging.warning') as mock_warning:
            # Act
            await graphiti_manager._run_cypher_query("MATCH (n) RETURN n")
            
            # Assert
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0]
            assert "Direct Cypher query execution detected" in call_args[0]
        
        # Cleanup
        del os.environ["GRAPHITI_ALLOW_CYPHER"]


class TestEpisodicAPIAdaptations:
    """Test existing functionality that needed to be adapted for episodic APIs."""
    
    @pytest_asyncio.fixture
    async def graphiti_manager(self):
        """Create a GraphitiManager instance for testing."""
        config = GraphitiConfig(
            database_url="bolt://localhost:7687",
            username="neo4j",
            password="password",
            database_name="neo4j"
        )
        manager = GraphitiManager(config)
        manager.client = Mock()
        yield manager
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_add_story_content_uses_episodic_api(self, graphiti_manager):
        """Test that add_story_content uses episodic APIs instead of direct node creation."""
        # Arrange
        mock_episode = Mock()
        mock_episode.uuid = "episode_123"
        graphiti_manager.client.add_episode = AsyncMock(return_value=mock_episode)
        graphiti_manager._story_sessions = {"test_story": "session_123"}
        
        content = "This is a test story."
        extracted_data = {
            "entities": [{"name": "Alice", "type": "character"}],
            "relationships": [{"from": "Alice", "to": "Bob", "type": "knows"}]
        }
        
        # Act
        result = await graphiti_manager.add_story_content(
            content, extracted_data, "test_story", "user_123"
        )
        
        # Assert
        assert result["status"] == "success"
        assert result["story_id"] == "test_story"
        assert result["entities_added"] == 1
        assert result["relationships_added"] == 1
        assert result["episode_id"] == "episode_123"
        
        # Verify add_episode was called correctly
        graphiti_manager.client.add_episode.assert_called_once()
        call_args = graphiti_manager.client.add_episode.call_args
        assert call_args.kwargs["name"] == "Story Content - test_story"
        assert "Story Content: This is a test story." in call_args.kwargs["episode_body"]
        assert call_args.kwargs["group_id"] == "session_123"
    
    @pytest.mark.asyncio
    async def test_extract_facts_uses_search_api(self, graphiti_manager):
        """Test that extract_facts uses search API instead of direct fact extraction."""
        # Arrange
        mock_result = Mock()
        mock_result.fact = "Alice knows Bob"
        mock_result.created_at = datetime.utcnow()
        mock_result.uuid = "fact_123"
        
        graphiti_manager.client.search = AsyncMock(return_value=[mock_result])
        graphiti_manager._story_sessions = {"test_story": "session_123"}
        
        content = "Alice knows Bob"
        
        # Act
        facts = await graphiti_manager.extract_facts("test_story", content)
        
        # Assert
        assert len(facts) == 1
        assert facts[0]["fact"] == "Alice knows Bob"
        assert facts[0]["uuid"] == "fact_123"
        assert facts[0]["confidence"] == 0.8
        
        # Verify search was called correctly
        graphiti_manager.client.search.assert_called_once_with(
            query="Alice knows Bob",
            group_ids=["session_123"],
            num_results=10
        )
    
    @pytest.mark.asyncio
    async def test_extract_facts_handles_no_session(self, graphiti_manager):
        """Test that extract_facts handles cases where no session exists."""
        # Arrange
        graphiti_manager._story_sessions = {}
        
        # Act
        facts = await graphiti_manager.extract_facts("nonexistent_story", "Some content")
        
        # Assert
        assert facts == []
    
    @pytest.mark.asyncio
    async def test_extract_facts_handles_search_errors(self, graphiti_manager):
        """Test that extract_facts handles search API errors gracefully."""
        # Arrange
        graphiti_manager.client.search = AsyncMock(side_effect=Exception("Search failed"))
        graphiti_manager._story_sessions = {"test_story": "session_123"}
        
        # Act
        facts = await graphiti_manager.extract_facts("test_story", "Some content")
        
        # Assert
        assert facts == []


class TestAPIEndpointIntegration:
    """Test API endpoints that use the refactored functionality."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_integration(self):
        """Test the /api/health endpoint integration."""
        from fastapi.testclient import TestClient
        
        with patch('app.main.graphiti_manager') as mock_graphiti, \
             patch('app.main.cinegraph_agent') as mock_agent, \
             patch('app.main.alert_manager') as mock_alerts:
            
            # Arrange
            mock_graphiti.health_check = AsyncMock(return_value={
                "status": "healthy",
                "connectivity_confirmed": True
            })
            mock_agent.health_check = AsyncMock(return_value={
                "status": "healthy"
            })
            mock_alerts.get_alert_stats.return_value = {
                "active_alerts": 0
            }
            
            client = TestClient(app)
            
            # Act
            response = client.get("/api/health")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "graphiti" in data
            assert "agent" in data
            assert "alerts" in data


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
