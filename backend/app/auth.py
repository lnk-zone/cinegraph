"""
Authentication and Rate Limiting Module
=======================================

This module handles JWT authentication with Supabase and rate limiting using Redis.
"""

import os
import redis
from datetime import datetime
from typing import Optional
from fastapi import HTTPException, Request, Header, Depends
from pydantic import BaseModel
from supabase import create_client, Client
from jose import JWTError, jwt

from celery_config import REDIS_HOST, REDIS_PORT, REDIS_DB

# Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Lazy initialization of Supabase client
supabase: Optional[Client] = None

def get_supabase_client() -> Client:
    """Get or create Supabase client instance"""
    global supabase
    if supabase is None:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return supabase

# Redis client for rate limiting
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

class User(BaseModel):
    """User model for JWT authentication"""
    id: str
    email: str

class TokenBucket:
    """Redis-based token bucket for rate limiting"""
    
    def __init__(self, capacity: int = 5, refill_rate: float = 5.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
    
    async def is_allowed(self, user_id: str) -> bool:
        """Check if request is allowed based on token bucket algorithm"""
        key = f"rate_limit:{user_id}"
        now = datetime.utcnow().timestamp()
        
        # Get current state
        bucket_data = redis_client.hgetall(key)
        
        if not bucket_data:
            # Initialize bucket
            tokens = self.capacity - 1  # Use 1 token for this request
            last_refill = now
        else:
            tokens = float(bucket_data.get("tokens", 0))
            last_refill = float(bucket_data.get("last_refill", now))
            
            # Calculate tokens to add based on time passed
            time_passed = now - last_refill
            tokens_to_add = time_passed * self.refill_rate
            tokens = min(self.capacity, tokens + tokens_to_add)
            
            # Check if we have enough tokens
            if tokens < 1:
                return False
            
            # Use 1 token
            tokens -= 1
        
        # Update bucket state
        redis_client.hset(key, mapping={
            "tokens": tokens,
            "last_refill": now
        })
        redis_client.expire(key, 60)  # Expire after 1 minute of inactivity
        
        return True

# Global token bucket instance
token_bucket = TokenBucket()

async def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    """Extract and validate JWT token from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else authorization
        
        # Verify JWT with Supabase
        user = get_supabase_client().auth.get_user(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return User(id=user.user.id, email=user.user.email)
    except (JWTError, IndexError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid token")

async def rate_limit_check(current_user: User) -> User:
    """Check rate limit for the current user"""
    if not await token_bucket.is_allowed(current_user.id):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Maximum 5 requests per second."
        )
    return current_user

async def verify_websocket_token(token: str) -> User:
    """Verify JWT token for WebSocket connections"""
    try:
        user = get_supabase_client().auth.get_user(token)
        if not user:
            raise ValueError("Invalid token")
        
        return User(id=user.user.id, email=user.user.email)
    except:
        raise ValueError("Invalid token")

# Combined dependency for auth + rate limiting
async def get_authenticated_user(authorization: Optional[str] = Header(None)) -> User:
    """Get current user with authentication only (no rate limiting)"""
    return await get_current_user(authorization)

async def get_rate_limited_user(current_user: User = Depends(get_authenticated_user)) -> User:
    """Get current user with both authentication and rate limiting"""
    return await rate_limit_check(current_user)
