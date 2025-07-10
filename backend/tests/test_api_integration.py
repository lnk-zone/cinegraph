"""
End-to-end API Integration Tests
===============================

This module contains comprehensive integration tests for the CineGraph API using httpx.AsyncClient
against a test FastAPI instance. These tests verify the complete API workflow from story analysis
to graph generation and contradiction detection.
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime
import json
import os
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from app.main import app
except ImportError:
    # Create a mock app if the real one doesn't exist
    from fastapi import FastAPI
    app = FastAPI()
    
try:
    from core.models import StoryInput, UserProfile
except ImportError:
    # Mock the models if they don't exist
    class StoryInput:
        pass
    class UserProfile:
        pass

try:
    from app.auth import User
except ImportError:
    # Mock the User class
    class User:
        def __init__(self, id, email):
            self.id = id
            self.email = email


# Mock user for testing
TEST_USER = User(
    id="test_user_001",
    email="test@example.com"
)


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_auth():
    """Mock authentication for testing."""
    with patch("app.auth.get_current_user", return_value=TEST_USER), \
         patch("app.auth.get_rate_limited_user", return_value=TEST_USER), \
         patch("app.auth.get_authenticated_user", return_value=TEST_USER), \
         patch("app.auth.redis_client") as mock_redis:
        # Configure Redis mock for rate limiting
        mock_redis.hgetall.return_value = {}  # Empty bucket data
        mock_redis.hset.return_value = None
        mock_redis.expire.return_value = None
        yield


@pytest.fixture
def mock_graphiti_manager():
    """Mock the GraphitiManager for testing."""
    mock_manager = AsyncMock()
    mock_manager.initialize.return_value = None
    mock_manager.health_check.return_value = {"status": "healthy"}
    mock_manager.get_story_graph.return_value = {
        "nodes": [
            {"id": "alice", "type": "CHARACTER", "name": "Alice"},
            {"id": "bob", "type": "CHARACTER", "name": "Bob"},
            {"id": "castle", "type": "LOCATION", "name": "Castle"},
        ],
        "edges": [
            {"from": "alice", "to": "bob", "type": "KNOWS"},
            {"from": "alice", "to": "castle", "type": "PRESENT_IN"},
            {"from": "bob", "to": "castle", "type": "PRESENT_IN"},
        ],
        "metadata": {"story_id": "test_story_001", "total_nodes": 3, "total_edges": 3}
    }
    mock_manager.get_character_knowledge.return_value = [
        {"knowledge_id": "k1", "content": "Alice knows Bob is a knight"},
        {"knowledge_id": "k2", "content": "Alice knows the castle has a secret passage"},
        {"knowledge_id": "k3", "content": "Alice remembers meeting Bob at the market"},
    ]
    mock_manager.detect_contradictions.return_value = {
        "status": "success",
        "contradictions_found": 0,
        "scan_duration": 0.45,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    with patch("app.main.graphiti_manager", mock_manager):
        yield mock_manager


@pytest.fixture
def mock_story_processor():
    """Mock the StoryProcessor for testing."""
    mock_processor = AsyncMock()
    mock_processor.process_story.return_value = {
        "entities": [
            {"id": "alice", "type": "CHARACTER", "name": "Alice"},
            {"id": "bob", "type": "CHARACTER", "name": "Bob"},
            {"id": "castle", "type": "LOCATION", "name": "Castle"},
        ],
        "relationships": [
            {"from": "alice", "to": "bob", "type": "KNOWS"},
            {"from": "alice", "to": "castle", "type": "PRESENT_IN"},
            {"from": "bob", "to": "castle", "type": "PRESENT_IN"},
        ],
        "metadata": {"processing_time": 1.23, "entities_count": 3, "relationships_count": 3}
    }
    
    with patch("app.main.story_processor", mock_processor):
        yield mock_processor


@pytest.fixture
def mock_cinegraph_agent():
    """Mock the CineGraphAgent for testing."""
    mock_agent = AsyncMock()
    mock_agent.initialize.return_value = None
    mock_agent.health_check.return_value = {"status": "healthy"}
    mock_agent.analyze_story.return_value = {
        "character_insights": [
            {"character": "Alice", "insight": "Protagonist with strong moral compass"},
            {"character": "Bob", "insight": "Supporting character, loyal knight"},
        ],
        "plot_insights": [
            {"type": "conflict", "description": "Alice must choose between duty and friendship"},
            {"type": "setting", "description": "Medieval castle provides atmospheric backdrop"},
        ],
        "consistency_score": 0.92,
        "recommendations": [
            "Consider expanding Bob's character background",
            "The castle setting could be described in more detail",
        ]
    }
    
    with patch("app.main.cinegraph_agent", mock_agent):
        yield mock_agent


@pytest.fixture
def mock_alert_manager():
    """Mock the alert manager for testing."""
    mock_manager = AsyncMock()
    mock_manager.start_listening.return_value = None
    mock_manager.get_alert_stats.return_value = {
        "total_alerts": 0,
        "active_listeners": 1,
        "system_status": "healthy"
    }
    
    with patch("app.main.alert_manager", mock_manager):
        yield mock_manager


@pytest.fixture
def two_paragraph_story():
    """Sample two-paragraph story for testing."""
    return """Alice walked through the ancient castle gates, her heart pounding with anticipation. The stone walls towered above her, covered in ivy and bearing the scars of countless battles. She had heard stories of this place since childhood - tales of brave knights, hidden treasures, and dark secrets buried within its depths. As she approached the main hall, she noticed a figure standing in the shadows. It was Bob, a knight she had met at the market just days before.

Bob stepped forward, his armor gleaming in the dim light filtering through the stained glass windows. "Alice, I didn't expect to see you here," he said, his voice echoing in the vast chamber. "This place holds many dangers, especially for someone unprepared." Alice smiled, remembering their conversation about the castle's legend. She had come here seeking answers about her family's past, and Bob's presence gave her courage. Together, they began to explore the mysterious corridors, unaware that their adventure would change both their lives forever."""


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests."""
    return {"Authorization": "Bearer mocked_jwt_token"}


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for the complete API workflow."""
    
    async def test_complete_api_workflow(
        self, 
        async_client: httpx.AsyncClient,
        mock_auth,
        mock_graphiti_manager,
        mock_story_processor,
        mock_cinegraph_agent,
        mock_alert_manager,
        two_paragraph_story: str,
        auth_headers: dict
    ):
        """Test the complete end-to-end API workflow."""
        
        # Step 1: POST /api/story/analyze with 2-paragraph prompt
        story_data = {
            "story_id": "test_story_001",
            "content": two_paragraph_story,
            "metadata": {"test": True}
        }
        
        response = await async_client.post("/api/story/analyze", json=story_data, headers=auth_headers)
        assert response.status_code == 200
        
        analyze_result = response.json()
        assert analyze_result["status"] == "success"
        assert "extracted_data" in analyze_result
        assert "insights" in analyze_result
        assert analyze_result["story_id"] == "test_story_001"
        
        # Verify that extracted data contains expected entities
        extracted_data = analyze_result["extracted_data"]
        assert len(extracted_data["entities"]) == 3
        assert len(extracted_data["relationships"]) == 3
        
        story_id = analyze_result["story_id"]
        
        # Step 2: GET /api/story/{id}/graph and assert node/edge counts > 0
        response = await async_client.get(f"/api/story/{story_id}/graph", headers=auth_headers)
        assert response.status_code == 200
        
        graph_result = response.json()
        assert graph_result["status"] == "success"
        assert "graph" in graph_result
        
        graph_data = graph_result["graph"]
        assert len(graph_data["nodes"]) > 0, "Graph should contain nodes"
        assert len(graph_data["edges"]) > 0, "Graph should contain edges"
        assert graph_data["metadata"]["total_nodes"] > 0
        assert graph_data["metadata"]["total_edges"] > 0
        
        # Step 3: GET /api/story/{id}/character/Alice/knowledge returns list
        response = await async_client.get(f"/api/story/{story_id}/character/Alice/knowledge", headers=auth_headers)
        assert response.status_code == 200
        
        knowledge_result = response.json()
        assert knowledge_result["status"] == "success"
        assert knowledge_result["character"] == "Alice"
        assert "knowledge" in knowledge_result
        assert isinstance(knowledge_result["knowledge"], list)
        assert len(knowledge_result["knowledge"]) > 0, "Alice should have knowledge items"
        
        # Verify knowledge structure
        for knowledge_item in knowledge_result["knowledge"]:
            assert "knowledge_id" in knowledge_item
            assert "content" in knowledge_item
        
        # Step 4: POST /api/story/{id}/detect_contradictions returns status=success
        response = await async_client.post(f"/api/story/{story_id}/detect_contradictions", headers=auth_headers)
        assert response.status_code == 200
        
        contradiction_result = response.json()
        assert contradiction_result["status"] == "success"
        assert "contradictions_found" in contradiction_result
        assert "scan_duration" in contradiction_result
        assert "timestamp" in contradiction_result
        assert isinstance(contradiction_result["contradictions_found"], int)
        
        # Verify mock calls were made
        mock_story_processor.process_story.assert_called_once()
        mock_cinegraph_agent.analyze_story.assert_called_once()
        mock_graphiti_manager.get_story_graph.assert_called_once()
        mock_graphiti_manager.get_character_knowledge.assert_called_once()
        mock_graphiti_manager.detect_contradictions.assert_called_once()


@pytest.mark.integration
class TestAPIEdgeCases:
    """Test edge cases and error conditions."""
    
    async def test_analyze_story_with_empty_content(
        self, 
        async_client: httpx.AsyncClient,
        mock_auth,
        mock_graphiti_manager,
        mock_story_processor,
        mock_cinegraph_agent,
        mock_alert_manager
    ):
        """Test story analysis with empty content."""
        story_data = {
            "story_id": "test_empty_story",
            "content": "",
        }
        
        response = await async_client.post("/api/story/analyze", json=story_data)
        # Should handle empty content gracefully
        assert response.status_code in [200, 400]
    
    async def test_get_nonexistent_story_graph(
        self, 
        async_client: httpx.AsyncClient,
        mock_auth,
        mock_graphiti_manager,
        mock_story_processor,
        mock_cinegraph_agent,
        mock_alert_manager
    ):
        """Test getting graph for non-existent story."""
        # Mock manager to return empty graph for non-existent story
        mock_graphiti_manager.get_story_graph.return_value = {
            "nodes": [],
            "edges": [],
            "metadata": {"story_id": "nonexistent", "total_nodes": 0, "total_edges": 0}
        }
        
        response = await async_client.get("/api/story/nonexistent_story/graph")
        assert response.status_code == 200
        
        graph_result = response.json()
        assert graph_result["status"] == "success"
        assert len(graph_result["graph"]["nodes"]) == 0
        assert len(graph_result["graph"]["edges"]) == 0
    
    async def test_get_character_knowledge_nonexistent_character(
        self, 
        async_client: httpx.AsyncClient,
        mock_auth,
        mock_graphiti_manager,
        mock_story_processor,
        mock_cinegraph_agent,
        mock_alert_manager
    ):
        """Test getting knowledge for non-existent character."""
        # Mock manager to return empty knowledge for non-existent character
        mock_graphiti_manager.get_character_knowledge.return_value = []
        
        response = await async_client.get("/api/story/test_story/character/NonExistent/knowledge")
        assert response.status_code == 200
        
        knowledge_result = response.json()
        assert knowledge_result["status"] == "success"
        assert knowledge_result["character"] == "NonExistent"
        assert isinstance(knowledge_result["knowledge"], list)
        assert len(knowledge_result["knowledge"]) == 0
    
    async def test_detect_contradictions_with_errors(
        self, 
        async_client: httpx.AsyncClient,
        mock_auth,
        mock_graphiti_manager,
        mock_story_processor,
        mock_cinegraph_agent,
        mock_alert_manager
    ):
        """Test contradiction detection with processing errors."""
        # Mock manager to simulate processing error
        mock_graphiti_manager.detect_contradictions.side_effect = Exception("Database connection error")
        
        response = await async_client.post("/api/story/test_story/detect_contradictions")
        assert response.status_code == 500
        
        error_result = response.json()
        assert "detail" in error_result
        assert "Database connection error" in error_result["detail"]


@pytest.mark.integration
class TestAPIAuthentication:
    """Test authentication and authorization."""
    
    async def test_endpoints_require_authentication(self, async_client: httpx.AsyncClient):
        """Test that protected endpoints require authentication."""
        # Test without mocking authentication
        endpoints_to_test = [
            ("POST", "/api/story/analyze", {"story_id": "test", "content": "test"}),
            ("GET", "/api/story/test/graph", None),
            ("GET", "/api/story/test/character/Alice/knowledge", None),
            ("POST", "/api/story/test/detect_contradictions", {}),
        ]
        
        for method, endpoint, data in endpoints_to_test:
            if method == "POST":
                response = await async_client.post(endpoint, json=data)
            else:
                response = await async_client.get(endpoint)
            
            # Should require authentication (401 or 403)
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require authentication"


@pytest.mark.integration
class TestAPIPerformance:
    """Test API performance and response times."""
    
    async def test_api_response_times(
        self, 
        async_client: httpx.AsyncClient,
        mock_auth,
        mock_graphiti_manager,
        mock_story_processor,
        mock_cinegraph_agent,
        mock_alert_manager,
        two_paragraph_story: str
    ):
        """Test that API responses are within acceptable time limits."""
        import time
        
        # Test story analysis performance
        start_time = time.time()
        story_data = {
            "story_id": "perf_test_story",
            "content": two_paragraph_story,
        }
        
        response = await async_client.post("/api/story/analyze", json=story_data)
        analysis_time = time.time() - start_time
        
        assert response.status_code == 200
        assert analysis_time < 5.0, f"Story analysis took {analysis_time:.2f}s, should be under 5s"
        
        story_id = response.json()["story_id"]
        
        # Test graph retrieval performance
        start_time = time.time()
        response = await async_client.get(f"/api/story/{story_id}/graph")
        graph_time = time.time() - start_time
        
        assert response.status_code == 200
        assert graph_time < 2.0, f"Graph retrieval took {graph_time:.2f}s, should be under 2s"
        
        # Test character knowledge retrieval performance
        start_time = time.time()
        response = await async_client.get(f"/api/story/{story_id}/character/Alice/knowledge")
        knowledge_time = time.time() - start_time
        
        assert response.status_code == 200
        assert knowledge_time < 2.0, f"Knowledge retrieval took {knowledge_time:.2f}s, should be under 2s"
        
        # Test contradiction detection performance
        start_time = time.time()
        response = await async_client.post(f"/api/story/{story_id}/detect_contradictions")
        contradiction_time = time.time() - start_time
        
        assert response.status_code == 200
        assert contradiction_time < 3.0, f"Contradiction detection took {contradiction_time:.2f}s, should be under 3s"


@pytest.mark.integration
class TestAPIDataValidation:
    """Test API data validation and error handling."""
    
    async def test_story_input_validation(
        self, 
        async_client: httpx.AsyncClient,
        mock_auth,
        mock_graphiti_manager,
        mock_story_processor,
        mock_cinegraph_agent,
        mock_alert_manager
    ):
        """Test story input validation."""
        # Test missing required fields
        invalid_inputs = [
            {},  # Empty payload
            {"story_id": "test"},  # Missing content
            {"content": "test"},  # Missing story_id
            {"story_id": "", "content": "test"},  # Empty story_id
            {"story_id": "test", "content": ""},  # Empty content
        ]
        
        for invalid_input in invalid_inputs:
            response = await async_client.post("/api/story/analyze", json=invalid_input)
            assert response.status_code in [400, 422], f"Should reject invalid input: {invalid_input}"
    
    async def test_character_name_validation(
        self, 
        async_client: httpx.AsyncClient,
        mock_auth,
        mock_graphiti_manager,
        mock_story_processor,
        mock_cinegraph_agent,
        mock_alert_manager
    ):
        """Test character name validation in knowledge endpoint."""
        # Test with various character names
        character_names = [
            "Alice",  # Valid
            "Bob Smith",  # Valid with space
            "Jean-Luc",  # Valid with hyphen
            "O'Connor",  # Valid with apostrophe
            "",  # Empty (should handle gracefully)
            "   ",  # Whitespace only
        ]
        
        for character_name in character_names:
            response = await async_client.get(f"/api/story/test_story/character/{character_name}/knowledge")
            # Should handle all character names (some may return empty results)
            assert response.status_code in [200, 400], f"Should handle character name: '{character_name}'"
    
    async def test_story_id_validation(
        self, 
        async_client: httpx.AsyncClient,
        mock_auth,
        mock_graphiti_manager,
        mock_story_processor,
        mock_cinegraph_agent,
        mock_alert_manager
    ):
        """Test story ID validation across endpoints."""
        # Test with various story IDs
        story_ids = [
            "valid_story_id",
            "story-with-hyphens",
            "story_with_underscores",
            "story123",
            "STORY_UPPERCASE",
            "story.with.dots",
        ]
        
        for story_id in story_ids:
            # Test graph endpoint
            response = await async_client.get(f"/api/story/{story_id}/graph")
            assert response.status_code in [200, 404], f"Should handle story ID: '{story_id}'"
            
            # Test contradiction detection endpoint
            response = await async_client.post(f"/api/story/{story_id}/detect_contradictions")
            assert response.status_code in [200, 404], f"Should handle story ID: '{story_id}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
