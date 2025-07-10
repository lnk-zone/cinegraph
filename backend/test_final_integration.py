#!/usr/bin/env python3
"""
Final API Integration Test
=========================

This is the working integration test for the CineGraph API.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

import httpx
from app.main import app
from app.auth import User

# Mock user and JWT token for testing
TEST_USER = User(
    id="test_user_001",
    email="test@example.com"
)
TEST_JWT_TOKEN = "mocked_jwt_token"

@pytest.mark.asyncio
async def test_complete_api_workflow():
    """Test the complete end-to-end API workflow with httpx.AsyncClient."""
    
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
            
            # Configure mocks
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
                "timestamp": "2024-01-01T00:00:00Z"
            })
            
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
            
            mock_alert_manager.start_listening = AsyncMock()
            mock_alert_manager.get_alert_stats = AsyncMock(return_value={
                "total_alerts": 0,
                "active_listeners": 1,
                "system_status": "healthy"
            })
            
            # Configure Redis mock
            mock_redis.hgetall.return_value = {}  # Empty bucket data
            mock_redis.hset.return_value = None
            mock_redis.expire.return_value = None
            
            # Test the API workflow
            async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                # Two-paragraph story content
                story_content = """Alice walked through the ancient castle gates, her heart pounding with anticipation. The stone walls towered above her, covered in ivy and bearing the scars of countless battles. She had heard stories of this place since childhood - tales of brave knights, hidden treasures, and dark secrets buried within its depths. As she approached the main hall, she noticed a figure standing in the shadows. It was Bob, a knight she had met at the market just days before.

Bob stepped forward, his armor gleaming in the dim light filtering through the stained glass windows. "Alice, I didn't expect to see you here," he said, his voice echoing in the vast chamber. "This place holds many dangers, especially for someone unprepared." Alice smiled, remembering their conversation about the castle's legend. She had come here seeking answers about her family's past, and Bob's presence gave her courage. Together, they began to explore the mysterious corridors, unaware that their adventure would change both their lives forever."""
                
                # Step 1: POST /api/story/analyze with 2-paragraph prompt
                story_data = {
                    "story_id": "test_story_001",
                    "content": story_content,
                    "metadata": {"test": True}
                }
                
                headers = {"Authorization": f"Bearer {TEST_JWT_TOKEN}"}
                response = await client.post("/api/story/analyze", json=story_data, headers=headers)
                if response.status_code != 200:
                    print(f"ERROR: Got status code {response.status_code}")
                    print(f"Response content: {response.text}")
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
                
                print("✅ All API integration tests passed!")
                print("✅ Successfully tested complete end-to-end workflow:")
                print("   1. POST /api/story/analyze with 2-paragraph prompt")
                print("   2. GET /api/story/{id}/graph with node/edge counts > 0")
                print("   3. GET /api/story/{id}/character/Alice/knowledge returns list")
                print("   4. POST /api/story/{id}/detect_contradictions returns status=success")


if __name__ == "__main__":
    asyncio.run(test_complete_api_workflow())
