"""
API Regression Tests - End-to-end Integration
============================================

This module contains comprehensive end-to-end API regression tests for the CineGraph API
using httpx.AsyncClient against a test FastAPI instance. These tests verify the complete 
API workflow from story analysis to graph generation and contradiction detection.

All tests are marked with pytest.mark.integration for selective test execution.
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
from app.main import app
from app.auth import User


# Mock user for testing
TEST_USER = User(
    id="test_user_001",
    email="test@example.com"
)

# Mock JWT token
TEST_JWT_TOKEN = "mocked_jwt_token"

# Two-paragraph story for testing
SAMPLE_STORY = """Alice walked through the ancient castle gates, her heart pounding with anticipation. The stone walls towered above her, covered in ivy and bearing the scars of countless battles. She had heard stories of this place since childhood - tales of brave knights, hidden treasures, and dark secrets buried within its depths. As she approached the main hall, she noticed a figure standing in the shadows. It was Bob, a knight she had met at the market just days before.

Bob stepped forward, his armor gleaming in the dim light filtering through the stained glass windows. "Alice, I didn't expect to see you here," he said, his voice echoing in the vast chamber. "This place holds many dangers, especially for someone unprepared." Alice smiled, remembering their conversation about the castle's legend. She had come here seeking answers about her family's past, and Bob's presence gave her courage. Together, they began to explore the mysterious corridors, unaware that their adventure would change both their lives forever."""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_api_workflow():
    """
    Test the complete end-to-end API workflow.
    
    This test verifies:
    1. POST /api/story/analyze with a 2-paragraph prompt
    2. GET /api/story/{id}/graph and assert node/edge counts > 0
    3. GET /api/story/{id}/character/Alice/knowledge returns list
    4. POST /api/story/{id}/detect_contradictions returns status=success
    """
    
    # Mock authentication and Redis
    with patch("app.auth.get_current_user", return_value=TEST_USER), \
         patch("app.auth.get_rate_limited_user", return_value=TEST_USER), \
         patch("app.auth.get_authenticated_user", return_value=TEST_USER), \
         patch("app.auth.redis_client") as mock_redis:
        
        # Mock the core components
        with patch("app.main.graphiti_manager") as mock_graphiti_manager, \
             patch("app.main.story_processor") as mock_story_processor, \
             patch("app.main.cinegraph_agent") as mock_cinegraph_agent, \
             patch("app.main.alert_manager") as mock_alert_manager:
            
            # Configure component mocks
            _configure_mocks(
                mock_graphiti_manager, 
                mock_story_processor, 
                mock_cinegraph_agent, 
                mock_alert_manager, 
                mock_redis
            )
            
            # Test the API workflow
            async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                headers = {"Authorization": f"Bearer {TEST_JWT_TOKEN}"}
                
                # Step 1: POST /api/story/analyze with 2-paragraph prompt
                story_data = {
                    "story_id": "test_story_001",
                    "content": SAMPLE_STORY,
                    "metadata": {"test": True}
                }
                
                response = await client.post("/api/story/analyze", json=story_data, headers=headers)
                assert response.status_code == 200
                
                analyze_result = response.json()
                assert analyze_result["status"] == "success"
                assert "extracted_data" in analyze_result
                assert "insights" in analyze_result
                assert analyze_result["story_id"] == "test_story_001"
                
                # Verify extracted data
                extracted_data = analyze_result["extracted_data"]
                assert len(extracted_data["entities"]) == 3
                assert len(extracted_data["relationships"]) == 3
                
                story_id = analyze_result["story_id"]
                
                # Step 2: GET /api/story/{id}/graph and assert node/edge counts > 0
                response = await client.get(f"/api/story/{story_id}/graph", headers=headers)
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
                response = await client.get(f"/api/story/{story_id}/character/Alice/knowledge", headers=headers)
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
                response = await client.post(f"/api/story/{story_id}/detect_contradictions", headers=headers)
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
@pytest.mark.asyncio
async def test_api_input_validation():
    """Test API input validation for edge cases."""
    
    with patch("app.auth.get_current_user", return_value=TEST_USER), \
         patch("app.auth.get_rate_limited_user", return_value=TEST_USER), \
         patch("app.auth.get_authenticated_user", return_value=TEST_USER), \
         patch("app.auth.redis_client") as mock_redis:
        
        with patch("app.main.graphiti_manager") as mock_graphiti_manager, \
             patch("app.main.story_processor") as mock_story_processor, \
             patch("app.main.cinegraph_agent") as mock_cinegraph_agent, \
             patch("app.main.alert_manager") as mock_alert_manager:
            
            _configure_mocks(
                mock_graphiti_manager, 
                mock_story_processor, 
                mock_cinegraph_agent, 
                mock_alert_manager, 
                mock_redis
            )
            
            async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                headers = {"Authorization": f"Bearer {TEST_JWT_TOKEN}"}
                
                # Test invalid input data
                invalid_inputs = [
                    {},  # Empty payload
                    {"story_id": "test"},  # Missing content
                    {"content": "test"},  # Missing story_id
                ]
                
                for invalid_input in invalid_inputs:
                    response = await client.post("/api/story/analyze", json=invalid_input, headers=headers)
                    assert response.status_code in [400, 422], f"Should reject invalid input: {invalid_input}"
                
                # Test edge case: empty story_id (may be acceptable as API can auto-generate)
                edge_case_input = {"story_id": "", "content": "test"}
                response = await client.post("/api/story/analyze", json=edge_case_input, headers=headers)
                # This may pass (200) if API auto-generates IDs, or fail (400/422) if validation rejects empty IDs
                assert response.status_code in [200, 400, 422], f"Edge case handling for empty story_id"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_error_handling():
    """Test API error handling for various failure scenarios."""
    
    with patch("app.auth.get_current_user", return_value=TEST_USER), \
         patch("app.auth.get_rate_limited_user", return_value=TEST_USER), \
         patch("app.auth.get_authenticated_user", return_value=TEST_USER), \
         patch("app.auth.redis_client") as mock_redis:
        
        with patch("app.main.graphiti_manager") as mock_graphiti_manager, \
             patch("app.main.story_processor") as mock_story_processor, \
             patch("app.main.cinegraph_agent") as mock_cinegraph_agent, \
             patch("app.main.alert_manager") as mock_alert_manager:
            
            # Configure Redis mock
            mock_redis.hgetall.return_value = {}
            mock_redis.hset.return_value = None
            mock_redis.expire.return_value = None
            
            # Configure other mocks
            mock_alert_manager.start_listening = AsyncMock()
            mock_alert_manager.get_alert_stats = AsyncMock(return_value={
                "total_alerts": 0,
                "active_listeners": 1,
                "system_status": "healthy"
            })
            
            # Test error scenario: graphiti manager failure
            mock_graphiti_manager.detect_contradictions = AsyncMock(
                side_effect=Exception("Database connection error")
            )
            
            async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                headers = {"Authorization": f"Bearer {TEST_JWT_TOKEN}"}
                
                response = await client.post("/api/story/test_story/detect_contradictions", headers=headers)
                assert response.status_code == 500
                
                error_result = response.json()
                assert "detail" in error_result
                assert "Database connection error" in error_result["detail"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authentication_required():
    """Test that API endpoints require authentication."""
    
    # Test without any authentication mocking
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        endpoints_to_test = [
            ("POST", "/api/story/analyze", {"story_id": "test", "content": "test"}),
            ("GET", "/api/story/test/graph", None),
            ("GET", "/api/story/test/character/Alice/knowledge", None),
            ("POST", "/api/story/test/detect_contradictions", {}),
        ]
        
        for method, endpoint, data in endpoints_to_test:
            if method == "POST":
                response = await client.post(endpoint, json=data)
            else:
                response = await client.get(endpoint)
            
            # Should require authentication (401 or 403)
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require authentication"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_performance():
    """Test API performance and response times."""
    
    with patch("app.auth.get_current_user", return_value=TEST_USER), \
         patch("app.auth.get_rate_limited_user", return_value=TEST_USER), \
         patch("app.auth.get_authenticated_user", return_value=TEST_USER), \
         patch("app.auth.redis_client") as mock_redis:
        
        with patch("app.main.graphiti_manager") as mock_graphiti_manager, \
             patch("app.main.story_processor") as mock_story_processor, \
             patch("app.main.cinegraph_agent") as mock_cinegraph_agent, \
             patch("app.main.alert_manager") as mock_alert_manager:
            
            _configure_mocks(
                mock_graphiti_manager, 
                mock_story_processor, 
                mock_cinegraph_agent, 
                mock_alert_manager, 
                mock_redis
            )
            
            async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                headers = {"Authorization": f"Bearer {TEST_JWT_TOKEN}"}
                
                import time
                
                # Test story analysis performance
                start_time = time.time()
                story_data = {"story_id": "perf_test_story", "content": SAMPLE_STORY}
                response = await client.post("/api/story/analyze", json=story_data, headers=headers)
                analysis_time = time.time() - start_time
                
                assert response.status_code == 200
                assert analysis_time < 5.0, f"Story analysis took {analysis_time:.2f}s, should be under 5s"
                
                story_id = response.json()["story_id"]
                
                # Test other endpoints performance
                endpoints = [
                    ("GET", f"/api/story/{story_id}/graph", 2.0),
                    ("GET", f"/api/story/{story_id}/character/Alice/knowledge", 2.0),
                    ("POST", f"/api/story/{story_id}/detect_contradictions", 3.0),
                ]
                
                for method, endpoint, max_time in endpoints:
                    start_time = time.time()
                    if method == "GET":
                        response = await client.get(endpoint, headers=headers)
                    else:
                        response = await client.post(endpoint, headers=headers)
                    elapsed_time = time.time() - start_time
                    
                    assert response.status_code == 200
                    assert elapsed_time < max_time, f"{endpoint} took {elapsed_time:.2f}s, should be under {max_time}s"


def _configure_mocks(mock_graphiti_manager, mock_story_processor, mock_cinegraph_agent, mock_alert_manager, mock_redis):
    """Configure all mocks with realistic return values."""
    
    # Configure GraphitiManager mock
    mock_graphiti_manager.initialize = AsyncMock()
    mock_graphiti_manager.health_check = AsyncMock(return_value={"status": "healthy"})
    mock_graphiti_manager.get_story_graph = AsyncMock(return_value={
        "nodes": [
            {"id": "alice", "type": "CHARACTER", "name": "Alice"},
            {"id": "bob", "type": "CHARACTER", "name": "Bob"},
            {"id": "castle", "type": "LOCATION", "name": "Castle"}
        ],
        "edges": [
            {"from": "alice", "to": "bob", "type": "KNOWS"},
            {"from": "alice", "to": "castle", "type": "PRESENT_IN"},
            {"from": "bob", "to": "castle", "type": "PRESENT_IN"}
        ],
        "metadata": {"story_id": "test_story_001", "total_nodes": 3, "total_edges": 3}
    })
    mock_graphiti_manager.get_character_knowledge = AsyncMock(return_value=[
        {"knowledge_id": "k1", "content": "Alice knows Bob is a knight"},
        {"knowledge_id": "k2", "content": "Alice knows the castle has a secret passage"},
        {"knowledge_id": "k3", "content": "Alice remembers meeting Bob at the market"}
    ])
    mock_graphiti_manager.detect_contradictions = AsyncMock(return_value={
        "status": "success",
        "contradictions_found": 0,
        "scan_duration": 0.45,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Configure StoryProcessor mock
    mock_story_processor.process_story = AsyncMock(return_value={
        "entities": [
            {"id": "alice", "type": "CHARACTER", "name": "Alice"},
            {"id": "bob", "type": "CHARACTER", "name": "Bob"},
            {"id": "castle", "type": "LOCATION", "name": "Castle"}
        ],
        "relationships": [
            {"from": "alice", "to": "bob", "type": "KNOWS"},
            {"from": "alice", "to": "castle", "type": "PRESENT_IN"},
            {"from": "bob", "to": "castle", "type": "PRESENT_IN"}
        ],
        "metadata": {"processing_time": 1.23, "entities_count": 3, "relationships_count": 3}
    })
    
    # Configure CineGraphAgent mock
    mock_cinegraph_agent.initialize = AsyncMock()
    mock_cinegraph_agent.health_check = AsyncMock(return_value={"status": "healthy"})
    mock_cinegraph_agent.analyze_story = AsyncMock(return_value={
        "character_insights": [
            {"character": "Alice", "insight": "Protagonist with strong moral compass"},
            {"character": "Bob", "insight": "Supporting character, loyal knight"}
        ],
        "plot_insights": [
            {"type": "conflict", "description": "Alice must choose between duty and friendship"},
            {"type": "setting", "description": "Medieval castle provides atmospheric backdrop"}
        ],
        "consistency_score": 0.92,
        "recommendations": [
            "Consider expanding Bob's character background",
            "The castle setting could be described in more detail"
        ]
    })
    
    # Configure AlertManager mock
    mock_alert_manager.start_listening = AsyncMock()
    mock_alert_manager.get_alert_stats = AsyncMock(return_value={
        "total_alerts": 0,
        "active_listeners": 1,
        "system_status": "healthy"
    })
    
    # Configure Redis mock
    mock_redis.hgetall.return_value = {}  # Empty bucket data for rate limiting
    mock_redis.hset.return_value = None
    mock_redis.expire.return_value = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
