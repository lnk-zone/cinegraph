"""
Test Authentication and Rate Limiting
=====================================

This module tests JWT authentication with Supabase and rate limiting using Redis.
It includes tests for:
1. Mocking Supabase JWT verification via monkeypatch
2. Rate limiting behavior (>5 requests/second to /api/health expects HTTP 429)
3. Redis connection error handling (surfaces as HTTP 500 with clear message)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import redis
import time

from app.main import app
from app.auth import get_current_user, get_rate_limited_user, get_authenticated_user, User, token_bucket, redis_client


class TestAuthenticationMocking:
    """Test JWT authentication mocking"""
    
    def test_mock_jwt_verification_success(self, monkeypatch):
        """Test successful JWT verification with mocked Supabase client"""
        # Mock the Supabase client and its auth.get_user method
        mock_user_response = Mock()
        mock_user_response.user = Mock()
        mock_user_response.user.id = "test-user-123"
        mock_user_response.user.email = "test@example.com"
        
        mock_supabase = Mock()
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": "test-user-123",
                "email": "test@example.com",
                "full_name": "Test User",
                "avatar_url": None,
                "created_at": "2023-01-01T00:00:00.000Z"
            }
        ]
        
        # Patch the get_supabase_client function
        monkeypatch.setattr("app.auth.get_supabase_client", lambda: mock_supabase)
        
        # Test authentication on protected endpoint
        client = TestClient(app)
        response = client.get("/api/users/me", headers={"Authorization": "Bearer valid-token"})
        
        # Should succeed with mocked JWT verification
        assert response.status_code == 200
        
        # Verify the mock was called appropriately
        mock_supabase.auth.get_user.assert_called_once_with("valid-token")
    
    def test_mock_jwt_verification_failure(self, monkeypatch):
        """Test JWT verification failure with mocked Supabase client"""
        # Mock the Supabase client to return None (invalid token)
        mock_supabase = Mock()
        mock_supabase.auth.get_user.return_value = None
        
        # Patch the get_supabase_client function
        monkeypatch.setattr("app.auth.get_supabase_client", lambda: mock_supabase)
        
        # Test authentication on protected endpoint
        client = TestClient(app)
        response = client.get("/api/users/me", headers={"Authorization": "Bearer invalid-token"})
        
        # Should fail with 401 Unauthorized
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]
    
    def test_mock_jwt_verification_missing_header(self):
        """Test JWT verification with missing Authorization header"""
        client = TestClient(app)
        response = client.get("/api/users/me")
        
        # Should fail with 401 Unauthorized
        assert response.status_code == 401
        assert "Authorization header missing" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_mock(self, monkeypatch):
        """Test get_current_user function with mocked dependencies"""
        # Mock the Supabase client and its auth.get_user method
        mock_user_response = Mock()
        mock_user_response.user = Mock()
        mock_user_response.user.id = "test-user-456"
        mock_user_response.user.email = "test2@example.com"
        
        mock_supabase = Mock()
        mock_supabase.auth.get_user.return_value = mock_user_response
        
        # Patch the get_supabase_client function
        monkeypatch.setattr("app.auth.get_supabase_client", lambda: mock_supabase)
        
        # Test the function directly
        user = await get_current_user("Bearer test-token")
        
        assert user.id == "test-user-456"
        assert user.email == "test2@example.com"
        mock_supabase.auth.get_user.assert_called_once_with("test-token")


class TestRateLimiting:
    """Test rate limiting behavior"""
    
    def test_rate_limit_under_threshold(self, monkeypatch):
        """Test that requests under rate limit threshold are allowed"""
        # Mock successful authentication
        def mock_get_current_user(authorization):
            return User(id="test-user-123", email="test@example.com")
        
        monkeypatch.setattr("app.auth.get_current_user", mock_get_current_user)
        
        # Create a mock Redis client that simulates successful rate limiting
        mock_redis = Mock()
        mock_redis.hgetall.return_value = {}  # Empty bucket data
        mock_redis.hset.return_value = True
        mock_redis.expire.return_value = True
        
        monkeypatch.setattr("app.auth.redis_client", mock_redis)
        
        client = TestClient(app)
        
        # Make 3 requests (under the limit of 5)
        for i in range(3):
            response = client.get("/api/health", headers={"Authorization": "Bearer test-token"})
            assert response.status_code == 200
            time.sleep(0.1)  # Small delay between requests
    
    def test_rate_limit_exceeded_returns_429(self, monkeypatch):
        """Test that >5 requests/second to /api/health returns HTTP 429"""
        # Mock successful authentication
        def mock_get_current_user(authorization):
            return User(id="test-user-rate-limit", email="test@example.com")
        
        monkeypatch.setattr("app.auth.get_current_user", mock_get_current_user)
        
        # Create a mock Redis client that simulates rate limiting
        mock_redis = Mock()
        request_count = 0
        
        def mock_hgetall(key):
            nonlocal request_count
            request_count += 1
            if request_count <= 5:
                return {}  # Empty bucket data for first 5 requests
            else:
                # Return bucket data showing no tokens available
                return {"tokens": "0", "last_refill": str(datetime.utcnow().timestamp())}
        
        mock_redis.hgetall.side_effect = mock_hgetall
        mock_redis.hset.return_value = True
        mock_redis.expire.return_value = True
        
        monkeypatch.setattr("app.auth.redis_client", mock_redis)
        
        client = TestClient(app)
        
        # Make requests rapidly to exceed rate limit
        responses = []
        for i in range(7):  # More than 5 requests
            response = client.get("/api/health", headers={"Authorization": "Bearer test-token"})
            responses.append(response)
        
        # First 5 requests should succeed
        for i in range(5):
            assert responses[i].status_code == 200
        
        # Additional requests should be rate limited (429)
        for i in range(5, 7):
            assert responses[i].status_code == 429
            assert "Rate limit exceeded" in responses[i].json()["detail"]
    
    def test_rate_limit_with_protected_endpoint(self, monkeypatch):
        """Test rate limiting on protected endpoints"""
        # Mock successful authentication and user profile
        def mock_get_current_user(authorization):
            return User(id="test-user-protected", email="test@example.com")
        
        mock_user_response = Mock()
        mock_user_response.user = Mock()
        mock_user_response.user.id = "test-user-protected"
        mock_user_response.user.email = "test@example.com"
        
        mock_supabase = Mock()
        mock_supabase.auth.get_user.return_value = mock_user_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": "test-user-protected",
                "email": "test@example.com",
                "full_name": "Test User",
                "avatar_url": None,
                "created_at": "2023-01-01T00:00:00.000Z"
            }
        ]
        
        monkeypatch.setattr("app.auth.get_current_user", mock_get_current_user)
        monkeypatch.setattr("app.auth.get_supabase_client", lambda: mock_supabase)
        
        # Reset Redis state for test user
        redis_client.delete("rate_limit:test-user-protected")
        
        client = TestClient(app)
        
        # Make requests rapidly to exceed rate limit
        responses = []
        for i in range(7):  # More than 5 requests
            response = client.get("/api/users/me", headers={"Authorization": "Bearer test-token"})
            responses.append(response)
        
        # First 5 requests should succeed
        for i in range(5):
            assert responses[i].status_code == 200
        
        # Additional requests should be rate limited (429)
        for i in range(5, 7):
            assert responses[i].status_code == 429
            assert "Rate limit exceeded" in responses[i].json()["detail"]
    
    @pytest.mark.asyncio
    async def test_token_bucket_algorithm(self, monkeypatch):
        """Test the token bucket rate limiting algorithm directly"""
        # Use a separate user ID for this test
        test_user_id = "test-token-bucket-user"
        
        # Create a mock Redis client that simulates token bucket behavior
        mock_redis = Mock()
        request_count = 0
        
        def mock_hgetall(key):
            nonlocal request_count
            request_count += 1
            if request_count <= 5:
                return {}  # Empty bucket data for first 5 requests
            else:
                # Return bucket data showing no tokens available
                return {"tokens": "0", "last_refill": str(datetime.utcnow().timestamp())}
        
        mock_redis.hgetall.side_effect = mock_hgetall
        mock_redis.hset.return_value = True
        mock_redis.expire.return_value = True
        
        monkeypatch.setattr("app.auth.redis_client", mock_redis)
        
        # Test initial requests (should be allowed)
        for i in range(5):
            allowed = await token_bucket.is_allowed(test_user_id)
            assert allowed is True
        
        # Test exceeding limit (should be denied)
        allowed = await token_bucket.is_allowed(test_user_id)
        assert allowed is False
        
        # Reset the mock for token refill simulation
        mock_redis.hgetall.side_effect = lambda key: {}  # Fresh bucket
        
        # Test again after "refill" (should be allowed)
        allowed = await token_bucket.is_allowed(test_user_id)
        assert allowed is True


class TestRedisErrorHandling:
    """Test Redis connection error handling"""
    
    def test_redis_connection_error_surfaces_as_500(self, monkeypatch):
        """Test that Redis connection errors surface as HTTP 500 with clear message"""
        # Mock successful authentication
        def mock_get_current_user(authorization):
            return User(id="test-user-redis-error", email="test@example.com")
        
        monkeypatch.setattr("app.auth.get_current_user", mock_get_current_user)
        
        # Create a mock Redis client that raises connection error
        mock_redis = Mock()
        mock_redis.hgetall.side_effect = redis.ConnectionError("Connection refused")
        
        # Override the auto-used mock with our error-raising mock
        monkeypatch.setattr("app.auth.redis_client", mock_redis)
        
        client = TestClient(app)
        
        # This should trigger the Redis error during rate limiting
        response = client.get("/api/health", headers={"Authorization": "Bearer test-token"})
        
        # Should result in HTTP 500 with clear error message
        assert response.status_code == 500
        assert "Connection refused" in response.json()["detail"]
    
    def test_redis_timeout_error_handling(self, monkeypatch):
        """Test Redis timeout error handling"""
        # Mock successful authentication
        def mock_get_current_user(authorization):
            return User(id="test-user-redis-timeout", email="test@example.com")
        
        monkeypatch.setattr("app.auth.get_current_user", mock_get_current_user)
        
        # Create a mock Redis client that raises timeout error
        mock_redis = Mock()
        mock_redis.hgetall.side_effect = redis.TimeoutError("Timeout occurred")
        
        # Override the auto-used mock with our error-raising mock
        monkeypatch.setattr("app.auth.redis_client", mock_redis)
        
        client = TestClient(app)
        
        # This should trigger the Redis timeout during rate limiting
        response = client.get("/api/health", headers={"Authorization": "Bearer test-token"})
        
        # Should result in HTTP 500 with clear error message
        assert response.status_code == 500
        assert "Timeout occurred" in response.json()["detail"]
    
    def test_redis_generic_error_handling(self, monkeypatch):
        """Test generic Redis error handling"""
        # Mock successful authentication
        def mock_get_current_user(authorization):
            return User(id="test-user-redis-generic", email="test@example.com")
        
        monkeypatch.setattr("app.auth.get_current_user", mock_get_current_user)
        
        # Create a mock Redis client that raises generic Redis error
        mock_redis = Mock()
        mock_redis.hgetall.side_effect = redis.RedisError("Generic Redis error")
        
        # Override the auto-used mock with our error-raising mock
        monkeypatch.setattr("app.auth.redis_client", mock_redis)
        
        client = TestClient(app)
        
        # This should trigger the Redis error during rate limiting
        response = client.get("/api/health", headers={"Authorization": "Bearer test-token"})
        
        # Should result in HTTP 500 with clear error message
        assert response.status_code == 500
        assert "Generic Redis error" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_token_bucket_redis_error_handling(self, monkeypatch):
        """Test token bucket Redis error handling directly"""
        # Create a mock Redis client that raises connection error
        mock_redis = Mock()
        mock_redis.hgetall.side_effect = redis.ConnectionError("Redis connection failed")
        
        # Override the auto-used mock with our error-raising mock
        monkeypatch.setattr("app.auth.redis_client", mock_redis)
        
        # Test that Redis error is properly propagated as HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await token_bucket.is_allowed("test-user-redis-direct")
        
        assert exc_info.value.status_code == 500
        assert "Redis connection failed" in str(exc_info.value.detail)


class TestIntegrationScenarios:
    """Integration tests combining authentication and rate limiting"""
    
    def test_unauthenticated_requests_not_rate_limited(self):
        """Test that unauthenticated requests bypass rate limiting"""
        client = TestClient(app)
        
        # Make many requests without authentication to health endpoint
        for i in range(10):
            response = client.get("/api/health")
            # Health endpoint doesn't require auth, so should always succeed
            assert response.status_code == 200
    
    def test_different_users_have_separate_rate_limits(self, monkeypatch):
        """Test that different users have separate rate limit buckets"""
        # Mock authentication for different users
        def mock_get_current_user_1(authorization):
            return User(id="user-1", email="user1@example.com")
        
        def mock_get_current_user_2(authorization):
            return User(id="user-2", email="user2@example.com")
        
        # Reset Redis state for both users
        redis_client.delete("rate_limit:user-1")
        redis_client.delete("rate_limit:user-2")
        
        client = TestClient(app)
        
        # Test user 1 - exhaust rate limit
        monkeypatch.setattr("app.auth.get_current_user", mock_get_current_user_1)
        
        for i in range(6):  # Exceed rate limit
            response = client.get("/api/health", headers={"Authorization": "Bearer token1"})
            if i < 5:
                assert response.status_code == 200
            else:
                assert response.status_code == 429
        
        # Test user 2 - should have separate rate limit
        monkeypatch.setattr("app.auth.get_current_user", mock_get_current_user_2)
        
        for i in range(5):  # Within rate limit
            response = client.get("/api/health", headers={"Authorization": "Bearer token2"})
            assert response.status_code == 200
    
    def test_websocket_token_verification(self, monkeypatch):
        """Test WebSocket token verification with mocked Supabase"""
        # Mock the Supabase client and its auth.get_user method
        mock_user_response = Mock()
        mock_user_response.user = Mock()
        mock_user_response.user.id = "websocket-user-123"
        mock_user_response.user.email = "ws@example.com"
        
        mock_supabase = Mock()
        mock_supabase.auth.get_user.return_value = mock_user_response
        
        # Patch the get_supabase_client function
        monkeypatch.setattr("app.auth.get_supabase_client", lambda: mock_supabase)
        
        # Test WebSocket connection with valid token
        client = TestClient(app)
        with client.websocket_connect("/api/alerts/stream?token=valid-ws-token") as websocket:
            # Connection should be successful
            # The websocket will close quickly due to lack of Redis pub/sub setup in tests
            pass
        
        # Verify the mock was called
        mock_supabase.auth.get_user.assert_called_with("valid-ws-token")


# Test fixtures and utilities
@pytest.fixture(autouse=True)
def mock_redis_client(monkeypatch):
    """Mock Redis client for testing without Redis server"""
    # Create a mock Redis client
    mock_redis = Mock()
    
    # Mock the basic Redis operations
    mock_redis.hgetall.return_value = {}
    mock_redis.hset.return_value = True
    mock_redis.expire.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.scan_iter.return_value = []
    mock_redis.ping.return_value = True
    
    # Patch the Redis client in the auth module
    monkeypatch.setattr("app.auth.redis_client", mock_redis)
    
    # Mock the alert manager to avoid Redis connection in health check
    mock_alert_manager = Mock()
    mock_alert_manager.get_alert_stats.return_value = {
        "redis_connected": True,
        "total_alerts": 0,
        "recent_alerts": []
    }
    monkeypatch.setattr("app.main.alert_manager", mock_alert_manager)
    
    # Mock the graphiti manager and cinegraph agent health checks
    async def mock_health_check():
        return {"status": "healthy"}
    
    monkeypatch.setattr("app.main.graphiti_manager.health_check", mock_health_check)
    monkeypatch.setattr("app.main.cinegraph_agent.health_check", mock_health_check)
    
    yield mock_redis


@pytest.fixture
def mock_user():
    """Fixture providing a mock user for testing"""
    return User(id="test-user-fixture", email="fixture@example.com")


@pytest.fixture
def authenticated_client(monkeypatch, mock_user):
    """Fixture providing an authenticated test client"""
    def mock_get_current_user(authorization):
        return mock_user
    
    monkeypatch.setattr("app.auth.get_current_user", mock_get_current_user)
    return TestClient(app)
