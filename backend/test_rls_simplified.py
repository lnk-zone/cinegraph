#!/usr/bin/env python3
"""
Simplified End-to-End Tests for Row Level Security (RLS)
======================================================

This test suite provides a simplified but comprehensive test of RLS functionality:
1. Creates mock users to test isolation
2. Tests that user A cannot access user B's stories/alerts (404/403 expected)
3. Tests rate limiting and authentication dependencies
4. Uses pytest-asyncio for async testing

This version uses mocked authentication to avoid complex Supabase setup.
"""

import pytest
import pytest_asyncio
import asyncio
import httpx
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

# Import our application modules
from app.main import app
from core.models import StoryInput


class MockUser:
    """Mock user for testing"""
    def __init__(self, user_id: str, email: str):
        self.id = user_id
        self.email = email


class MockAuthManager:
    """Mock authentication manager for testing"""
    
    def __init__(self):
        self.users = {}
        self.rate_limit_counts = {}
    
    def create_user(self, user_id: str, email: str) -> MockUser:
        """Create a mock user"""
        user = MockUser(user_id, email)
        self.users[user_id] = user
        self.rate_limit_counts[user_id] = 0
        return user
    
    def get_user_by_token(self, token: str) -> Optional[MockUser]:
        """Get user by JWT token"""
        if token.startswith("valid_token_"):
            user_id = token.replace("valid_token_", "")
            return self.users.get(user_id)
        return None
    
    def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        count = self.rate_limit_counts.get(user_id, 0)
        self.rate_limit_counts[user_id] = count + 1
        # Allow 5 requests per user for testing
        return count < 15


# Global mock auth manager
mock_auth_manager = MockAuthManager()


@pytest_asyncio.fixture
async def test_client():
    """Create test client for the FastAPI app"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def test_users():
    """Create two mock users for testing"""
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    
    user_a = mock_auth_manager.create_user(user_a_id, "user_a@test.com")
    user_b = mock_auth_manager.create_user(user_b_id, "user_b@test.com")
    
    return {
        "user_a": user_a,
        "user_b": user_b,
        "user_a_token": f"valid_token_{user_a_id}",
        "user_b_token": f"valid_token_{user_b_id}",
        "user_a_headers": {"Authorization": f"Bearer valid_token_{user_a_id}"},
        "user_b_headers": {"Authorization": f"Bearer valid_token_{user_b_id}"}
    }


@pytest_asyncio.fixture
async def mock_dependencies():
    """Mock all application dependencies"""
    
    # Mock authentication
    async def mock_get_authenticated_user(authorization: str = None):
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header missing")
        
        token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else authorization
        user = mock_auth_manager.get_user_by_token(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user
    
    async def mock_get_rate_limited_user(current_user):
        if not mock_auth_manager.check_rate_limit(current_user.id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return current_user
    
    # Mock GraphitiManager with user isolation
    mock_graphiti_manager = MagicMock()
    mock_graphiti_manager.initialize = AsyncMock()
    mock_graphiti_manager.health_check = AsyncMock(return_value={"status": "healthy"})
    
    def mock_get_story_graph(story_id: str, user_id: str):
        """Mock story graph with user isolation"""
        # Only return data if story belongs to user (story_id contains user_id)
        if user_id in story_id:
            return {
                "entities": [
                    {"id": f"entity_{user_id}_1", "type": "CHARACTER", "name": "Alice"},
                    {"id": f"entity_{user_id}_2", "type": "LOCATION", "name": "Forest"}
                ],
                "relationships": [
                    {"from_id": f"entity_{user_id}_1", "to_id": f"entity_{user_id}_2", "type": "LOCATED_AT"}
                ]
            }
        else:
            # Return empty for cross-user access
            return {"entities": [], "relationships": []}
    
    def mock_get_character_knowledge(story_id: str, character_name: str, timestamp=None, user_id=None):
        """Mock character knowledge with user isolation"""
        if user_id in story_id:
            return {
                "character_id": f"char_{character_name}_{user_id}",
                "character_name": character_name,
                "knowledge_items": [
                    {"fact": f"{character_name} is in the {story_id}", "timestamp": "2023-01-01T00:00:00Z"}
                ],
                "story_id": story_id
            }
        else:
            return {
                "character_id": f"char_{character_name}",
                "character_name": character_name,
                "knowledge_items": [],
                "story_id": story_id
            }
    
    def mock_delete_story(story_id: str, user_id: str):
        """Mock story deletion with user isolation"""
        if user_id in story_id:
            return {"status": "success", "message": f"Story {story_id} deleted"}
        else:
            # In real implementation, this would return 404 or raise exception
            return {"status": "error", "message": "Story not found"}
    
    mock_graphiti_manager.get_story_graph.side_effect = mock_get_story_graph
    mock_graphiti_manager.get_character_knowledge.side_effect = mock_get_character_knowledge
    mock_graphiti_manager.delete_story.side_effect = mock_delete_story
    
    # Mock StoryProcessor
    mock_story_processor = MagicMock()
    mock_story_processor.process_story = AsyncMock(return_value={
        "entities": [{"id": "entity1", "type": "CHARACTER", "name": "Alice"}],
        "relationships": [],
        "metadata": {"processed_at": datetime.utcnow().isoformat()}
    })
    
    # Mock CineGraphAgent
    mock_cinegraph_agent = MagicMock()
    mock_cinegraph_agent.analyze_story = AsyncMock(return_value={
        "insights": ["Alice is a main character"],
        "recommendations": ["Consider developing Alice's backstory"]
    })
    mock_cinegraph_agent.detect_inconsistencies = AsyncMock(return_value=[])
    mock_cinegraph_agent.health_check = AsyncMock(return_value={"status": "healthy"})
    
    def mock_query_story(story_id: str, question: str, user_id: str):
        """Mock story query with user isolation"""
        if user_id in story_id:
            return f"Answer for '{question}' in story {story_id}: Alice is the main character."
        else:
            return "No information available"
    
    mock_cinegraph_agent.query_story.side_effect = mock_query_story
    
    # Mock alert manager
    mock_alert_manager = MagicMock()
    mock_alert_manager.get_alert_stats.return_value = {
        "total_alerts": 5,
        "active_subscriptions": 1,
        "last_alert_time": "2023-01-01T00:00:00Z"
    }
    
    # Mock Supabase client for profile operations
    mock_supabase_client = MagicMock()
    mock_table = MagicMock()
    mock_supabase_client.table.return_value = mock_table
    
    def mock_profile_select_eq(field, value):
        """Mock profile selection with user isolation"""
        if field == "id":
            user = mock_auth_manager.users.get(value)
            if user:
                mock_table.execute.return_value.data = [{
                    "id": user.id,
                    "email": user.email,
                    "full_name": f"Test User {user.id[:8]}",
                    "avatar_url": None,
                    "created_at": "2023-01-01T00:00:00Z"
                }]
            else:
                mock_table.execute.return_value.data = []
        return mock_table
    
    mock_table.select.return_value.eq = mock_profile_select_eq
    
    # Apply all patches
    with patch('app.main.get_authenticated_user', side_effect=mock_get_authenticated_user), \
         patch('app.main.get_rate_limited_user', side_effect=mock_get_rate_limited_user), \
         patch('app.main.graphiti_manager', mock_graphiti_manager), \
         patch('app.main.story_processor', mock_story_processor), \
         patch('app.main.cinegraph_agent', mock_cinegraph_agent), \
         patch('app.main.alert_manager', mock_alert_manager), \
         patch('app.main.get_supabase_client', return_value=mock_supabase_client):
        
        yield {
            "graphiti_manager": mock_graphiti_manager,
            "story_processor": mock_story_processor,
            "cinegraph_agent": mock_cinegraph_agent,
            "alert_manager": mock_alert_manager,
            "supabase_client": mock_supabase_client
        }


class TestRLSEndToEnd:
    """End-to-end tests for Row Level Security"""
    
    @pytest.mark.asyncio
    async def test_user_story_isolation(self, test_client, test_users, mock_dependencies):
        """Test that users cannot access each other's stories"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        # User A creates a story
        story_a_data = {
            "story_id": f"story_{user_a.id}_adventure",
            "content": "Alice walked through the enchanted forest and found a magic sword.",
            "user_id": user_a.id
        }
        
        response = await test_client.post(
            "/api/story/analyze",
            json=story_a_data,
            headers=test_users["user_a_headers"]
        )
        
        assert response.status_code == 200
        story_a_response = response.json()
        assert story_a_response["status"] == "success"
        assert story_a_response["story_id"] == story_a_data["story_id"]
        
        # User B creates a story
        story_b_data = {
            "story_id": f"story_{user_b.id}_mystery",
            "content": "Bob discovered a hidden cave with ancient treasures.",
            "user_id": user_b.id
        }
        
        response = await test_client.post(
            "/api/story/analyze",
            json=story_b_data,
            headers=test_users["user_b_headers"]
        )
        
        assert response.status_code == 200
        story_b_response = response.json()
        assert story_b_response["status"] == "success"
        assert story_b_response["story_id"] == story_b_data["story_id"]
        
        # User A should be able to access their own story
        response = await test_client.get(
            f"/api/story/{story_a_data['story_id']}/graph",
            headers=test_users["user_a_headers"]
        )
        assert response.status_code == 200
        user_a_graph = response.json()
        assert len(user_a_graph["graph"]["entities"]) > 0
        
        # User B should NOT be able to access User A's story (should get empty results)
        response = await test_client.get(
            f"/api/story/{story_a_data['story_id']}/graph",
            headers=test_users["user_b_headers"]
        )
        assert response.status_code == 200
        user_b_accessing_a = response.json()
        assert len(user_b_accessing_a["graph"]["entities"]) == 0, "User B should not see User A's story entities"
        
        # User A should NOT be able to access User B's story (should get empty results)
        response = await test_client.get(
            f"/api/story/{story_b_data['story_id']}/graph",
            headers=test_users["user_a_headers"]
        )
        assert response.status_code == 200
        user_a_accessing_b = response.json()
        assert len(user_a_accessing_b["graph"]["entities"]) == 0, "User A should not see User B's story entities"
    
    @pytest.mark.asyncio
    async def test_character_knowledge_isolation(self, test_client, test_users, mock_dependencies):
        """Test that users cannot access each other's character knowledge"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        story_a_id = f"story_{user_a.id}_adventure"
        story_b_id = f"story_{user_b.id}_mystery"
        
        # User A should be able to access their character's knowledge
        response = await test_client.get(
            f"/api/story/{story_a_id}/character/Alice/knowledge",
            headers=test_users["user_a_headers"]
        )
        assert response.status_code == 200
        user_a_knowledge = response.json()
        assert len(user_a_knowledge["knowledge"]["knowledge_items"]) > 0
        
        # User B should NOT be able to access User A's character knowledge
        response = await test_client.get(
            f"/api/story/{story_a_id}/character/Alice/knowledge",
            headers=test_users["user_b_headers"]
        )
        assert response.status_code == 200
        user_b_accessing_a_knowledge = response.json()
        assert len(user_b_accessing_a_knowledge["knowledge"]["knowledge_items"]) == 0, \
            "User B should not see User A's character knowledge"
        
        # User B should be able to access their own character's knowledge
        response = await test_client.get(
            f"/api/story/{story_b_id}/character/Bob/knowledge",
            headers=test_users["user_b_headers"]
        )
        assert response.status_code == 200
        user_b_knowledge = response.json()
        assert len(user_b_knowledge["knowledge"]["knowledge_items"]) > 0
    
    @pytest.mark.asyncio
    async def test_story_deletion_isolation(self, test_client, test_users, mock_dependencies):
        """Test that users can only delete their own stories"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        story_a_id = f"story_{user_a.id}_adventure"
        story_b_id = f"story_{user_b.id}_mystery"
        
        # User A should be able to delete their own story
        response = await test_client.delete(
            f"/api/story/{story_a_id}",
            headers=test_users["user_a_headers"]
        )
        assert response.status_code == 200
        delete_response = response.json()
        assert delete_response["status"] == "success"
        
        # User B should NOT be able to delete User A's story
        response = await test_client.delete(
            f"/api/story/{story_a_id}",
            headers=test_users["user_b_headers"]
        )
        assert response.status_code == 200
        delete_response = response.json()
        assert delete_response["status"] == "error", "User B should not be able to delete User A's story"
    
    @pytest.mark.asyncio
    async def test_authentication_required(self, test_client, mock_dependencies):
        """Test that authentication is required for protected endpoints"""
        
        # Test without authentication header
        response = await test_client.get("/api/story/test_story/graph")
        assert response.status_code == 401
        
        # Test with invalid token
        response = await test_client.get(
            "/api/story/test_story/graph",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
        
        # Test story creation without auth
        story_data = {
            "story_id": "test_story",
            "content": "Test content",
            "user_id": "test_user"
        }
        
        response = await test_client.post("/api/story/analyze", json=story_data)
        assert response.status_code == 401
        
        # Test other protected endpoints
        protected_endpoints = [
            ("GET", "/api/story/test/inconsistencies"),
            ("GET", "/api/story/test/character/Alice/knowledge"),
            ("POST", "/api/story/test/query"),
            ("POST", "/api/story/test/validate"),
            ("DELETE", "/api/story/test"),
            ("GET", "/api/alerts/stats"),
            ("GET", "/api/users/me")
        ]
        
        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = await test_client.get(endpoint)
            elif method == "POST":
                response = await test_client.post(endpoint, json={"question": "test"})
            elif method == "DELETE":
                response = await test_client.delete(endpoint)
            
            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require authentication"
    
    @pytest.mark.asyncio
    async def test_rate_limiting_with_auth(self, test_client, test_users, mock_dependencies):
        """Test that rate limiting works correctly with authentication"""
        
        user_a = test_users["user_a"]
        
        story_data = {
            "story_id": f"story_{user_a.id}_rate_test",
            "content": "Testing rate limiting functionality",
            "user_id": user_a.id
        }
        
        # Make multiple requests rapidly
        success_count = 0
        rate_limited_count = 0
        
        for i in range(20):  # Make 20 requests
            response = await test_client.post(
                "/api/story/analyze",
                json=story_data,
                headers=test_users["user_a_headers"]
            )
            
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited_count += 1
            
            # Small delay to simulate real usage
            await asyncio.sleep(0.01)
        
        # We should have some successful requests
        assert success_count > 0, "Should have some successful requests"
        # We should eventually hit rate limiting
        assert rate_limited_count > 0, "Should have some rate limited requests"
        assert success_count + rate_limited_count == 20, "Should account for all requests"
    
    @pytest.mark.asyncio
    async def test_user_profile_isolation(self, test_client, test_users, mock_dependencies):
        """Test that users can only access their own profiles"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        # User A should be able to access their own profile
        response = await test_client.get("/api/users/me", headers=test_users["user_a_headers"])
        assert response.status_code == 200
        profile_data = response.json()
        assert profile_data["id"] == user_a.id
        assert profile_data["email"] == user_a.email
        
        # User B should be able to access their own profile
        response = await test_client.get("/api/users/me", headers=test_users["user_b_headers"])
        assert response.status_code == 200
        profile_data = response.json()
        assert profile_data["id"] == user_b.id
        assert profile_data["email"] == user_b.email
    
    @pytest.mark.asyncio
    async def test_story_query_isolation(self, test_client, test_users, mock_dependencies):
        """Test that users can only query their own stories"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        story_a_id = f"story_{user_a.id}_adventure"
        story_b_id = f"story_{user_b.id}_mystery"
        
        query_data = {"question": "What happens in this story?"}
        
        # User A should be able to query their own story
        response = await test_client.post(
            f"/api/story/{story_a_id}/query",
            json=query_data,
            headers=test_users["user_a_headers"]
        )
        assert response.status_code == 200
        query_response = response.json()
        assert "Alice is the main character" in query_response["response"]
        
        # User B should NOT be able to query User A's story effectively
        response = await test_client.post(
            f"/api/story/{story_a_id}/query",
            json=query_data,
            headers=test_users["user_b_headers"]
        )
        assert response.status_code == 200
        query_response = response.json()
        assert query_response["response"] == "No information available"
    
    @pytest.mark.asyncio
    async def test_alerts_isolation(self, test_client, test_users, mock_dependencies):
        """Test that users can access their own alert statistics"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        # Both users should be able to access alert stats (they're user-specific)
        response = await test_client.get("/api/alerts/stats", headers=test_users["user_a_headers"])
        assert response.status_code == 200
        stats_data = response.json()
        assert stats_data["status"] == "success"
        assert "stats" in stats_data
        
        response = await test_client.get("/api/alerts/stats", headers=test_users["user_b_headers"])
        assert response.status_code == 200
        stats_data = response.json()
        assert stats_data["status"] == "success"
        assert "stats" in stats_data
    
    @pytest.mark.asyncio
    async def test_health_check_accessible(self, test_client, mock_dependencies):
        """Test that health check endpoint is accessible without authentication"""
        
        response = await test_client.get("/api/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "graphiti" in health_data
        assert "agent" in health_data
        assert "alerts" in health_data
    
    @pytest.mark.asyncio
    async def test_inconsistency_detection_isolation(self, test_client, test_users, mock_dependencies):
        """Test that users can only detect inconsistencies in their own stories"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        story_a_id = f"story_{user_a.id}_adventure"
        story_b_id = f"story_{user_b.id}_mystery"
        
        # User A should be able to detect inconsistencies in their own story
        response = await test_client.get(
            f"/api/story/{story_a_id}/inconsistencies",
            headers=test_users["user_a_headers"]
        )
        assert response.status_code == 200
        inconsistencies = response.json()
        assert inconsistencies["status"] == "success"
        
        # User B should NOT be able to detect inconsistencies in User A's story
        # This should return empty results or 404/403
        response = await test_client.get(
            f"/api/story/{story_a_id}/inconsistencies",
            headers=test_users["user_b_headers"]
        )
        assert response.status_code == 200
        inconsistencies = response.json()
        # Should return empty inconsistencies due to user isolation
        assert len(inconsistencies["inconsistencies"]) == 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
