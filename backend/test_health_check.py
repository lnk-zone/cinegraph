#!/usr/bin/env python3
"""
Simple health check script to test HTTP endpoints
"""
import httpx
import asyncio

async def test_health_endpoint():
    """Test the health endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_health_endpoint_sync():
    """Test the health endpoint synchronously"""
    try:
        response = httpx.get("http://localhost:8000/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("🏥 Testing Health Endpoint")
    print("=" * 40)
    
    # Try sync first
    print("Testing with httpx (sync):")
    success = test_health_endpoint_sync()
    
    if success:
        print("✅ Health endpoint working!")
    else:
        print("❌ Health endpoint not working or server not running")
