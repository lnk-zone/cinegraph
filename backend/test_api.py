#!/usr/bin/env python3
"""
Simple test script to demonstrate the API functionality.
This script shows how to:
1. Connect to the WebSocket endpoint with JWT authentication
2. Test rate limiting
3. Test the alert system
"""

import asyncio
import websockets
import json
import requests
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/alerts/stream"

# Mock JWT token for testing (replace with actual Supabase JWT)
TEST_JWT_TOKEN = "your_jwt_token_here"

async def test_websocket_connection():
    """Test WebSocket connection with JWT authentication"""
    print("Testing WebSocket connection...")
    
    try:
        # Connect to WebSocket with JWT token
        uri = f"{WS_URL}?token={TEST_JWT_TOKEN}"
        
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connection established")
            
            # Listen for alerts for 10 seconds
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    print(f"📢 Received alert: {message}")
                    
            except asyncio.TimeoutError:
                print("⏰ No alerts received in 10 seconds")
                
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")

def test_rate_limiting():
    """Test rate limiting functionality"""
    print("\nTesting rate limiting...")
    
    headers = {
        "Authorization": f"Bearer {TEST_JWT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test story data
    story_data = {
        "content": "This is a test story for rate limiting.",
        "story_id": "test_story_rate_limit",
        "user_id": "test_user_001"
    }
    
    # Make rapid requests to test rate limiting
    success_count = 0
    rate_limited_count = 0
    
    for i in range(10):
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/story/analyze",
                json=story_data,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                success_count += 1
                print(f"✓ Request {i+1}: Success")
            elif response.status_code == 429:
                rate_limited_count += 1
                print(f"⚠️ Request {i+1}: Rate limited")
            else:
                print(f"❌ Request {i+1}: Error {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request {i+1}: Connection error - {e}")
            
        # Small delay between requests
        time.sleep(0.1)
    
    print(f"\n📊 Rate limiting test results:")
    print(f"   Successful requests: {success_count}")
    print(f"   Rate limited requests: {rate_limited_count}")
    print(f"   Total requests: {success_count + rate_limited_count}")

def test_health_check():
    """Test health check endpoint"""
    print("\nTesting health check...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            print("✓ Health check successful:")
            print(f"   Status: {health_data.get('status')}")
            print(f"   Graphiti: {health_data.get('graphiti')}")
            print(f"   Agent: {health_data.get('agent')}")
            print(f"   Alerts: {health_data.get('alerts')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check connection error: {e}")

def test_alert_stats():
    """Test alert statistics endpoint"""
    print("\nTesting alert statistics...")
    
    headers = {
        "Authorization": f"Bearer {TEST_JWT_TOKEN}"
    }
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/alerts/stats",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            stats_data = response.json()
            print("✓ Alert stats retrieved successfully:")
            print(f"   {json.dumps(stats_data, indent=2)}")
        elif response.status_code == 401:
            print("❌ Authentication failed - check JWT token")
        else:
            print(f"❌ Alert stats failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Alert stats connection error: {e}")

async def main():
    """Run all tests"""
    print("🚀 Starting API tests...")
    print("=" * 50)
    
    # Test basic health check first
    test_health_check()
    
    # Test authentication with alert stats
    test_alert_stats()
    
    # Test rate limiting
    test_rate_limiting()
    
    # Test WebSocket connection
    await test_websocket_connection()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\nNote: Some tests may fail if:")
    print("- The API server is not running")
    print("- The JWT token is invalid or expired")
    print("- Redis is not running")
    print("- Supabase credentials are not configured")

if __name__ == "__main__":
    asyncio.run(main())
