"""
Test CineGraphAgent Implementation
==================================

Tests for the CineGraphAgent OpenAI SDK integration.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agents.cinegraph_agent import CineGraphAgent
from agents.query_tools import GraphQueryTools
from agents.alert_manager import AlertManager
from agents.story_analysis_agent import StoryAnalysisAgent
try:
    from agents.agent_factory import create_cinegraph_agent, initialize_cinegraph_agent
except ImportError:
    # Mock these if they don't exist
    def create_cinegraph_agent(*args, **kwargs):
        return CineGraphAgent(*args, **kwargs)
    def initialize_cinegraph_agent(*args, **kwargs):
        pass

from core.graphiti_manager import GraphitiManager
from core.models import GraphitiConfig


def test_agent_inherits_mixins():
    """Ensure CineGraphAgent inherits the new mixin classes."""
    assert issubclass(CineGraphAgent, StoryAnalysisAgent)
    assert issubclass(CineGraphAgent, AlertManager)
    assert issubclass(CineGraphAgent, GraphQueryTools)


class TestCineGraphAgent:
    """Test cases for CineGraphAgent functionality."""

    @pytest.fixture
    def mock_graphiti_manager(self):
        """Create a mock GraphitiManager."""
        manager = Mock(spec=GraphitiManager)
        manager.client = Mock()
        manager.client.query = AsyncMock(return_value=[])
        manager.client.search = AsyncMock(return_value=[{"result": "test"}])
        manager.client.retrieve_episodes = AsyncMock(return_value=[])
        manager._run_cypher_query = AsyncMock(return_value=[{"result": "test"}])
        manager._story_sessions = {"story_123": "session_123"}
        manager.health_check = AsyncMock(return_value={"status": "healthy"})
        manager.initialize = AsyncMock()
        return manager

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = Mock()
        client.chat.completions.create = AsyncMock()
        return client

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        client = Mock()
        client.table.return_value.insert.return_value.execute.return_value = {"data": []}
        client.table.return_value.select.return_value.execute.return_value = {"data": []}
        return client

    @pytest.fixture
    def agent(self, mock_graphiti_manager, mock_openai_client, mock_supabase_client):
        """Create a CineGraphAgent instance with mocks."""
        with patch('agents.cinegraph_agent.AsyncOpenAI', return_value=mock_openai_client), \
             patch('agents.cinegraph_agent.create_client', return_value=mock_supabase_client), \
             patch('agents.alert_manager.alert_manager') as mock_alert_manager:
            import agents.story_analysis_agent as sa
            sa.alert_manager = mock_alert_manager
            # Mock the alert manager to avoid Redis connection
            mock_alert_manager.start_listening = AsyncMock()
            mock_alert_manager.add_alert_handler = Mock()
            
            agent = CineGraphAgent(
                graphiti_manager=mock_graphiti_manager,
                openai_api_key="test_key",
                supabase_url="test_url",
                supabase_key="test_key"
            )
            return agent

    @pytest.mark.asyncio
    async def test_initialize_agent(self, agent):
        """Test agent initialization."""
        await agent.initialize()
        assert agent.graphiti_manager is not None
        assert agent.openai_client is not None
        assert agent.supabase is not None

    @pytest.mark.asyncio
    async def test_graph_query_tool(self, agent):
        """Test graph query tool functionality."""
        # Mock search result for episodic API
        agent.graphiti_manager.client.search = AsyncMock(return_value=[{"result": "test"}])
        
        result = await agent.graph_query(
            "MATCH (n {story_id: $story_id}) RETURN n",
            {"story_id": "test_story"}
        )
        
        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_health_check(self, agent, mock_openai_client):
        """Test health check functionality."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        health = await agent.health_check()
        assert health["status"] == "healthy"
        assert "components" in health
        assert "timestamp" in health


    @pytest.mark.asyncio
    async def test_narrative_context_tool(self, agent):
        """Test narrative context tool functionality."""
        mock_result = Mock()
        mock_result.episode_body = "Scene 1 content"
        mock_result.created_at = datetime.utcnow()
        mock_result.uuid = "fact_123"

        agent.graphiti_manager.client.retrieve_episodes = AsyncMock(return_value=[mock_result])
        agent.graphiti_manager._story_sessions = {"story_123": "session_123"}

        result = await agent.narrative_context("story_123")
        
        assert "Scene 1 content" in result

    @pytest.mark.asyncio
    async def test_analyze_story(self, agent, mock_openai_client):
        """Test story analysis functionality."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Analysis result"
        mock_response.choices[0].message.function_call = None
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        story_content = "Test story content"
        extracted_data = {"story_id": "test_story", "entities": []}
        
        result = await agent.analyze_story(story_content, extracted_data)
        
        assert result["analysis"] == "Analysis result"
        assert result["story_id"] == "test_story"
        assert "timestamp" in result
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_inconsistencies(self, agent, mock_openai_client):
        """Test inconsistency detection functionality."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Inconsistencies found"
        mock_response.choices[0].message.function_call = None
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = await agent.detect_inconsistencies("test_story", "user_123")
        
        assert result["inconsistencies"] == "Inconsistencies found"
        assert result["story_id"] == "test_story"
        assert "timestamp" in result
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_story(self, agent, mock_openai_client):
        """Test story querying functionality."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Query answer"
        mock_response.choices[0].message.function_call = None
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = await agent.query_story("test_story", "What happened?", "user_123")
        
        assert result["answer"] == "Query answer"
        assert result["question"] == "What happened?"
        assert result["story_id"] == "test_story"
        assert "timestamp" in result
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_story_consistency(self, agent, mock_openai_client):
        """Test story consistency validation functionality."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Validation report"
        mock_response.choices[0].message.function_call = None
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        result = await agent.validate_story_consistency("test_story", "user_123")
        
        assert result["validation_report"] == "Validation report"
        assert result["story_id"] == "test_story"
        assert "timestamp" in result
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_alert(self, agent, mock_openai_client):
        """Test Redis alert handling functionality."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Alert explanation"
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        alert_data = {
            "id": "test_alert",
            "story_id": "test_story",
            "alert_type": "contradiction_detected",
            "reason": "Test contradiction",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await agent._handle_alert(alert_data)
        
        # Verify OpenAI was called for enrichment
        mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify Supabase insert was called
        agent.supabase.table.assert_called_with("alerts")

    def test_assess_alert_severity(self, agent):
        """Test alert severity assessment."""
        # Test critical severity
        alert_data = {"reason": "Critical error detected"}
        severity = agent._assess_alert_severity(alert_data)
        assert severity == "critical"
        
        # Test high severity
        alert_data = {"reason": "Significant conflict found"}
        severity = agent._assess_alert_severity(alert_data)
        assert severity == "high"
        
        # Test medium severity
        alert_data = {"reason": "Minor inconsistency"}
        severity = agent._assess_alert_severity(alert_data)
        assert severity == "medium"
        
        # Test low severity (default)
        alert_data = {"reason": "Some other issue"}
        severity = agent._assess_alert_severity(alert_data)
        assert severity == "low"

    @pytest.mark.asyncio
    async def test_function_call_execution(self, agent):
        """Test function call execution."""
        # Mock function call
        function_call = Mock()
        function_call.name = "graph_query"
        function_call.arguments = (
            '{"cypher_query": "MATCH (n {story_id: $story_id}) RETURN n", "params": {"story_id": "test_story"}}'
        )
        
        # Mock search result for episodic API
        agent.graphiti_manager.client.search = AsyncMock(return_value=[{"result": "test"}])
        
        result = await agent._execute_function_call(function_call, "test_story")
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_error_handling(self, agent, mock_openai_client):
        """Test error handling in agent methods."""
        # Mock OpenAI to raise an exception
        mock_openai_client.chat.completions.create.side_effect = Exception("OpenAI error")
        
        # Test analyze_story error handling
        result = await agent.analyze_story("content", {"story_id": "test"})
        assert "error" in result
        assert result["error"] == "OpenAI error"
        
        # Test query_story error handling
        result = await agent.query_story("test", "question", "user_123")
        assert "error" in result
        assert result["error"] == "OpenAI error"


class TestAgentFactory:
    """Test cases for agent factory functions."""

    @patch.dict("os.environ", {
        "OPENAI_API_KEY": "test_key",
        "SUPABASE_URL": "test_url",
        "SUPABASE_SERVICE_ROLE_KEY": "test_key"
    })
    def test_create_cinegraph_agent(self):
        """Test agent creation via factory."""
        with patch('agents.agent_factory.GraphitiManager'), \
             patch('agents.cinegraph_agent.AsyncOpenAI'), \
             patch('agents.cinegraph_agent.create_client'), \
             patch('agents.alert_manager.alert_manager'):
            
            agent = create_cinegraph_agent()
            assert agent is not None
            assert isinstance(agent, CineGraphAgent)

    def test_create_cinegraph_agent_missing_env(self):
        """Test agent creation with missing environment variables."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
                create_cinegraph_agent()

    @patch.dict("os.environ", {
        "OPENAI_API_KEY": "test_key",
        "SUPABASE_URL": "test_url",
        "SUPABASE_SERVICE_ROLE_KEY": "test_key"
    })
    @pytest.mark.asyncio
    async def test_initialize_cinegraph_agent(self):
        """Test agent initialization via factory."""
        with patch('agents.agent_factory.GraphitiManager') as mock_manager, \
             patch('agents.cinegraph_agent.AsyncOpenAI'), \
             patch('agents.cinegraph_agent.create_client'), \
             patch('agents.alert_manager.alert_manager'):
            
            # Mock GraphitiManager methods
            mock_manager.return_value.initialize = AsyncMock()
            
            agent = create_cinegraph_agent()
            
            # Mock agent initialize method
            agent.initialize = AsyncMock()
            
            initialized_agent = await initialize_cinegraph_agent(agent)
            
            assert initialized_agent is not None
            agent.initialize.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
