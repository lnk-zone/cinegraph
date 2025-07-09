#!/usr/bin/env python3
"""
Test script for user profile endpoints
"""

import requests
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_TOKEN = "your-test-jwt-token-here"  # Replace with actual JWT token

def test_get_user_profile():
    """Test GET /api/users/me endpoint"""
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{BASE_URL}/api/users/me", headers=headers)
    
    print("GET /api/users/me")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print("-" * 50)
    
    return response

def test_update_user_profile():
    """Test PUT /api/users/me endpoint"""
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    update_data = {
        "full_name": "Test User Updated",
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    response = requests.put(
        f"{BASE_URL}/api/users/me", 
        headers=headers,
        json=update_data
    )
    
    print("PUT /api/users/me")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print("-" * 50)
    
    return response

def test_partial_update():
    """Test partial update with only one field"""
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    update_data = {
        "full_name": "Test User Partial Update"
    }
    
    response = requests.put(
        f"{BASE_URL}/api/users/me", 
        headers=headers,
        json=update_data
    )
    
    print("PUT /api/users/me (partial)")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print("-" * 50)
    
    return response

if __name__ == "__main__":
    print("Testing User Profile Endpoints")
    print("=" * 50)
    
    # Note: These tests will only work with a valid JWT token
    # and when the FastAPI server is running
    
    try:
        # Test getting user profile
        get_response = test_get_user_profile()
        
        # Test updating user profile
        update_response = test_update_user_profile()
        
        # Test partial update
        partial_response = test_partial_update()
        
        print("All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Make sure the FastAPI server is running.")
    except Exception as e:
        print(f"Error: {e}")
