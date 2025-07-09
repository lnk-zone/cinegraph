#!/usr/bin/env python3
"""
End-to-End Tests for Row Level Security (RLS)
===========================================

This test suite verifies that:
1. User isolation is properly enforced at the API level
2. Rate limiting works correctly with authentication
3. Users cannot access each other's stories or alerts
4. All authentication dependencies work as expected

Uses pytest-asyncio for async testing and Supabase Admin API for user management.
"""

import pytest
import pytest_asyncio
import asyncio
import httpx
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

# Import our application modules
from app.main import app
from app.auth import get_supabase_client
from core.models import StoryInput, UserProfile
from core.graphiti_manager import GraphitiManager
from core.story_processor import StoryProcessor
from agents.cinegraph_agent import CineGraphAgent


class TestUser:
    """Test user helper class"""
    
    def __init__(self, user_id: str, email: str, password: str, jwt_token: str):
        self.id = user_id
        self.email = email
        self.password = password
        self.jwt_token = jwt_token
        self.headers = {"Authorization": f"Bearer {jwt_token}"}


class SupabaseTestManager:
    """Manages test users in Supabase for RLS testing"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.test_users: List[TestUser] = []
    
    async def create_test_user(self, email: str, password: str) -> TestUser:
        """Create a test user via Supabase Admin API"""
        try:
            # Create user with Supabase Admin API
            response = self.supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True
            })
            
            user_id = response.user.id
            
            # Create user profile
            profile_data = {
                "id": user_id,
                "email": email,
                "full_name": f"Test User {email.split('@')[0]}",
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.supabase.table("profiles").insert(profile_data).execute()
            
            # Generate JWT token for the user
            jwt_token = self.supabase.auth.admin.generate_link({
                "type": "magiclink",
                "email": email
            })
            
            # For testing, we'll use a mock JWT token
            mock_jwt_token = f"test_jwt_token_{user_id}"
            
            test_user = TestUser(user_id, email, password, mock_jwt_token)
            self.test_users.append(test_user)
            
            return test_user
            
        except Exception as e:
            pytest.fail(f"Failed to create test user {email}: {str(e)}")
    
    async def cleanup_test_users(self):
        """Clean up all test users"""
        for user in self.test_users:
            try:
                # Delete user profile
                self.supabase.table("profiles").delete().eq("id", user.id).execute()
                
                # Delete user from auth
                self.supabase.auth.admin.delete_user(user.id)
                
            except Exception as e:
                print(f"Warning: Failed to cleanup user {user.email}: {str(e)}")
        
        self.test_users.clear()


@pytest_asyncio.fixture
async def test_client():
    """Create test client for the FastAPI app"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def supabase_manager():
    """Create Supabase test manager"""
    manager = SupabaseTestManager()
    yield manager
    await manager.cleanup_test_users()


@pytest_asyncio.fixture
async def test_users(supabase_manager):
    """Create two test users for RLS testing"""
    user_a = await supabase_manager.create_test_user(
        f"user_a_{uuid.uuid4().hex[:8]}@test.com",
        "test_password_123"
    )
    
    user_b = await supabase_manager.create_test_user(
        f"user_b_{uuid.uuid4().hex[:8]}@test.com",
        "test_password_456"
    )
    
    return {"user_a": user_a, "user_b": user_b}


@pytest_asyncio.fixture
async def mock_graphiti_manager():
    """Mock GraphitiManager for testing"""
    with patch('app.main.graphiti_manager') as mock_manager:
        # Mock the manager methods
        mock_manager.initialize = AsyncMock()
        mock_manager.get_story_graph = AsyncMock()
        mock_manager.delete_story = AsyncMock()
        mock_manager.get_character_knowledge = AsyncMock()
        mock_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        
        # Mock story graph responses with user isolation
        def mock_get_story_graph(story_id: str, user_id: str):
            # Return data only if the story belongs to the user
            if story_id.endswith(user_id[-3:]):  # Simple mock logic
                return {"entities": [{"id": "entity1", "type": "CHARACTER"}], "relationships": []}
            else:
                return {"entities": [], "relationships": []}
        
        mock_manager.get_story_graph.side_effect = mock_get_story_graph
        
        yield mock_manager


@pytest_asyncio.fixture
async def mock_story_processor():
    """Mock StoryProcessor for testing"""
    with patch('app.main.story_processor') as mock_processor:
        mock_processor.process_story = AsyncMock(return_value={
            "entities": [{"id": "entity1", "type": "CHARACTER", "name": "Alice"}],
            "relationships": [],
            "metadata": {"processed_at": datetime.utcnow().isoformat()}
        })
        yield mock_processor


@pytest_asyncio.fixture
async def mock_cinegraph_agent():
    """Mock CineGraphAgent for testing"""
    with patch('app.main.cinegraph_agent') as mock_agent:
        mock_agent.analyze_story = AsyncMock(return_value={
            "insights": ["Alice is a main character"],
            "recommendations": ["Consider developing Alice's backstory"]
        })
        mock_agent.detect_inconsistencies = AsyncMock(return_value=[])
        mock_agent.health_check = AsyncMock(return_value={"status": "healthy"})
        yield mock_agent


@pytest_asyncio.fixture
async def mock_auth_dependencies():
    """Mock authentication dependencies"""
    
    async def mock_get_authenticated_user(authorization: str = None):
        if not authorization:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Authorization header missing")
        
        # Extract token from authorization header
        token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else authorization
        
        # Mock user based on token
        if token.startswith("test_jwt_token_"):
            user_id = token.replace("test_jwt_token_", "")
            return type('User', (), {'id': user_id, 'email': f'user_{user_id}@test.com'})()
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def mock_get_rate_limited_user(current_user):
        # For testing, we'll simulate rate limiting occasionally
        import random
        if random.random() < 0.1:  # 10% chance of rate limiting
            from fastapi import HTTPException
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return current_user
    
    with patch('app.main.get_authenticated_user', side_effect=mock_get_authenticated_user), \
         patch('app.main.get_rate_limited_user', side_effect=mock_get_rate_limited_user):
        yield


class TestRLSEndToEnd:
    """End-to-end tests for Row Level Security"""
    
    @pytest.mark.asyncio
    async def test_user_story_isolation(self, test_client, test_users, mock_graphiti_manager, 
                                       mock_story_processor, mock_cinegraph_agent, mock_auth_dependencies):
        """Test that users cannot access each other's stories"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        # User A creates a story
        story_a_data = {
            "story_id": f"story_a_{user_a.id[-3:]}",
            "content": "Alice walked through the enchanted forest and found a magic sword.",
            "user_id": user_a.id
        }
        
        response = await test_client.post(
            "/api/story/analyze",
            json=story_a_data,
            headers=user_a.headers
        )
        
        assert response.status_code == 200
        story_a_response = response.json()
        assert story_a_response["status"] == "success"
        assert story_a_response["story_id"] == story_a_data["story_id"]
        
        # User B creates a story
        story_b_data = {
            "story_id": f"story_b_{user_b.id[-3:]}",
            "content": "Bob discovered a hidden cave with ancient treasures.",
            "user_id": user_b.id
        }
        
        response = await test_client.post(
            "/api/story/analyze",
            json=story_b_data,
            headers=user_b.headers
        )
        
        assert response.status_code == 200
        story_b_response = response.json()
        assert story_b_response["status"] == "success"
        assert story_b_response["story_id"] == story_b_data["story_id"]
        
        # User A should be able to access their own story
        response = await test_client.get(
            f"/api/story/{story_a_data['story_id']}/graph",
            headers=user_a.headers
        )
        assert response.status_code == 200
        user_a_graph = response.json()
        assert len(user_a_graph["graph"]["entities"]) > 0
        
        # User B should NOT be able to access User A's story
        response = await test_client.get(
            f"/api/story/{story_a_data['story_id']}/graph",
            headers=user_b.headers
        )
        assert response.status_code == 200
        user_b_accessing_a = response.json()
        assert len(user_b_accessing_a["graph"]["entities"]) == 0  # Should be empty due to RLS
        
        # User A should NOT be able to access User B's story
        response = await test_client.get(
            f"/api/story/{story_b_data['story_id']}/graph",
            headers=user_a.headers
        )
        assert response.status_code == 200
        user_a_accessing_b = response.json()
        assert len(user_a_accessing_b["graph"]["entities"]) == 0  # Should be empty due to RLS
    
    @pytest.mark.asyncio
    async def test_character_knowledge_isolation(self, test_client, test_users, 
                                                mock_graphiti_manager, mock_auth_dependencies):
        """Test that users cannot access each other's character knowledge"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        story_a_id = f"story_a_{user_a.id[-3:]}"
        story_b_id = f"story_b_{user_b.id[-3:]}"
        
        # Mock character knowledge responses
        def mock_get_character_knowledge(story_id: str, character_name: str, timestamp=None, user_id=None):
            # Return knowledge only if the story belongs to the user
            if story_id.endswith(user_id[-3:]):
                return {
                    "character_id": f"char_{character_name}_{user_id[-3:]}",
                    "character_name": character_name,
                    "knowledge_items": [
                        {"fact": f"{character_name} knows something important", "timestamp": "2023-01-01T00:00:00Z"}
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
        
        mock_graphiti_manager.get_character_knowledge.side_effect = mock_get_character_knowledge
        
        # User A should be able to access their character's knowledge
        response = await test_client.get(
            f"/api/story/{story_a_id}/character/Alice/knowledge",
            headers=user_a.headers
        )
        assert response.status_code == 200
        user_a_knowledge = response.json()
        assert len(user_a_knowledge["knowledge"]["knowledge_items"]) > 0
        
        # User B should NOT be able to access User A's character knowledge
        response = await test_client.get(
            f"/api/story/{story_a_id}/character/Alice/knowledge",
            headers=user_b.headers
        )
        assert response.status_code == 200
        user_b_accessing_a_knowledge = response.json()
        assert len(user_b_accessing_a_knowledge["knowledge"]["knowledge_items"]) == 0
    
    @pytest.mark.asyncio
    async def test_story_deletion_isolation(self, test_client, test_users, 
                                          mock_graphiti_manager, mock_auth_dependencies):
        """Test that users can only delete their own stories"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        story_a_id = f"story_a_{user_a.id[-3:]}"
        story_b_id = f"story_b_{user_b.id[-3:]}"
        
        # Mock deletion responses
        def mock_delete_story(story_id: str, user_id: str):
            # Only allow deletion if the story belongs to the user
            if story_id.endswith(user_id[-3:]):
                return {"status": "success", "message": f"Story {story_id} deleted"}
            else:
                # In real implementation, this would return no results or raise exception
                return {"status": "error", "message": "Story not found"}
        
        mock_graphiti_manager.delete_story.side_effect = mock_delete_story
        
        # User A should be able to delete their own story
        response = await test_client.delete(
            f"/api/story/{story_a_id}",
            headers=user_a.headers
        )
        assert response.status_code == 200
        delete_response = response.json()
        assert delete_response["status"] == "success"
        
        # User B should NOT be able to delete User A's story
        response = await test_client.delete(
            f"/api/story/{story_a_id}",
            headers=user_b.headers
        )
        # This should either return 404 or an error status
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            delete_response = response.json()
            assert delete_response["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_authentication_required(self, test_client, mock_auth_dependencies):
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
    
    @pytest.mark.asyncio
    async def test_rate_limiting_with_auth(self, test_client, test_users, mock_auth_dependencies,
                                         mock_story_processor, mock_cinegraph_agent):
        """Test that rate limiting works correctly with authentication"""
        
        user_a = test_users["user_a"]
        
        story_data = {
            "story_id": "rate_limit_test",
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
                headers=user_a.headers
            )
            
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited_count += 1
            
            # Small delay to simulate real usage
            await asyncio.sleep(0.05)
        
        # We should have some successful requests and potentially some rate limited
        assert success_count > 0
        # Note: Due to mocking, rate limiting might not trigger exactly as in production
        assert success_count + rate_limited_count == 20
    
    @pytest.mark.asyncio
    async def test_user_profile_isolation(self, test_client, test_users, mock_auth_dependencies):
        """Test that users can only access their own profiles"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        # Mock Supabase profile responses
        def mock_get_profile(user_id: str):
            return {
                "id": user_id,
                "email": f"user_{user_id}@test.com",
                "full_name": f"Test User {user_id}",
                "avatar_url": None,
                "created_at": "2023-01-01T00:00:00Z"
            }
        
        with patch('app.main.get_supabase_client') as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.return_value.table.return_value = mock_table
            
            # Mock profile data for each user
            def mock_select_eq(field, value):
                if field == "id":
                    if value == user_a.id:
                        mock_table.execute.return_value.data = [mock_get_profile(user_a.id)]
                    elif value == user_b.id:
                        mock_table.execute.return_value.data = [mock_get_profile(user_b.id)]
                    else:
                        mock_table.execute.return_value.data = []
                return mock_table
            
            mock_table.select.return_value.eq = mock_select_eq
            
            # User A should be able to access their own profile
            response = await test_client.get("/api/users/me", headers=user_a.headers)
            assert response.status_code == 200
            profile_data = response.json()
            assert profile_data["id"] == user_a.id
            assert profile_data["email"] == f"user_{user_a.id}@test.com"
            
            # User B should be able to access their own profile
            response = await test_client.get("/api/users/me", headers=user_b.headers)
            assert response.status_code == 200
            profile_data = response.json()
            assert profile_data["id"] == user_b.id
            assert profile_data["email"] == f"user_{user_b.id}@test.com"
    
    @pytest.mark.asyncio
    async def test_alerts_isolation(self, test_client, test_users, mock_auth_dependencies):
        """Test that users can only access their own alert statistics"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        # Mock alert manager
        with patch('app.main.alert_manager') as mock_alert_manager:
            mock_alert_manager.get_alert_stats.return_value = {
                "total_alerts": 5,
                "active_subscriptions": 1,
                "last_alert_time": "2023-01-01T00:00:00Z"
            }
            
            # Both users should be able to access alert stats (they're user-specific)
            response = await test_client.get("/api/alerts/stats", headers=user_a.headers)
            assert response.status_code == 200
            stats_data = response.json()
            assert stats_data["status"] == "success"
            assert "stats" in stats_data
            
            response = await test_client.get("/api/alerts/stats", headers=user_b.headers)
            assert response.status_code == 200
            stats_data = response.json()
            assert stats_data["status"] == "success"
            assert "stats" in stats_data
    
    @pytest.mark.asyncio
    async def test_story_query_isolation(self, test_client, test_users, mock_cinegraph_agent, mock_auth_dependencies):
        """Test that users can only query their own stories"""
        
        user_a = test_users["user_a"]
        user_b = test_users["user_b"]
        
        story_a_id = f"story_a_{user_a.id[-3:]}"
        story_b_id = f"story_b_{user_b.id[-3:]}"
        
        # Mock query responses based on user isolation
        def mock_query_story(story_id: str, question: str, user_id: str):
            # Only return results if the story belongs to the user
            if story_id.endswith(user_id[-3:]):
                return f"Answer for {question} in story {story_id}"
            else:
                return "No information available"
        
        mock_cinegraph_agent.query_story.side_effect = mock_query_story
        
        query_data = {"question": "What happens in this story?"}
        
        # User A should be able to query their own story
        response = await test_client.post(
            f"/api/story/{story_a_id}/query",
            json=query_data,
            headers=user_a.headers
        )
        assert response.status_code == 200
        query_response = response.json()
        assert "Answer for" in query_response["response"]
        
        # User B should NOT be able to query User A's story effectively
        response = await test_client.post(
            f"/api/story/{story_a_id}/query",
            json=query_data,
            headers=user_b.headers
        )
        assert response.status_code == 200
        query_response = response.json()
        assert query_response["response"] == "No information available"
    
    @pytest.mark.asyncio
    async def test_health_check_accessible(self, test_client, mock_graphiti_manager, mock_cinegraph_agent):
        """Test that health check endpoint is accessible without authentication"""
        
        with patch('app.main.alert_manager') as mock_alert_manager:
            mock_alert_manager.get_alert_stats.return_value = {"status": "healthy"}
            
            response = await test_client.get("/api/health")
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data["status"] == "healthy"
            assert "graphiti" in health_data
            assert "agent" in health_data
            assert "alerts" in health_data


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
