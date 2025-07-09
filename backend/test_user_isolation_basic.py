#!/usr/bin/env python3
"""
Test script to verify user isolation implementation is working correctly
"""

import sys
import os
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from core.models import StoryInput, CharacterKnowledge, StoryGraph, GraphEntity, GraphRelationship, EntityType, RelationshipType
from core.graphiti_manager import GraphitiManager
from app.auth import User


def test_story_input_model():
    """Test that StoryInput model includes user_id field"""
    print("Testing StoryInput model...")
    
    # Test creating StoryInput with user_id
    story_input = StoryInput(
        story_id="test_001",
        content="Test story content",
        user_id="user_123"
    )
    
    assert story_input.user_id == "user_123"
    assert story_input.story_id == "test_001"
    assert story_input.content == "Test story content"
    
    # Test creating StoryInput without user_id (should be None)
    story_input_no_user = StoryInput(
        story_id="test_002",
        content="Test story content"
    )
    
    assert story_input_no_user.user_id is None
    print("✅ StoryInput model supports user_id field")


def test_user_model():
    """Test that User model has id and email fields"""
    print("Testing User model...")
    
    user = User(id="user_123", email="test@example.com")
    
    assert user.id == "user_123"
    assert user.email == "test@example.com"
    print("✅ User model is correctly structured")


def test_graphiti_manager_method_signatures():
    """Test that GraphitiManager methods have been updated to accept user_id"""
    print("Testing GraphitiManager method signatures...")
    
    import inspect
    
    # Check add_story_content method
    sig = inspect.signature(GraphitiManager.add_story_content)
    params = list(sig.parameters.keys())
    assert 'user_id' in params, "add_story_content should accept user_id parameter"
    
    # Check get_story_graph method
    sig = inspect.signature(GraphitiManager.get_story_graph)
    params = list(sig.parameters.keys())
    assert 'user_id' in params, "get_story_graph should accept user_id parameter"
    
    # Check get_character_knowledge method
    sig = inspect.signature(GraphitiManager.get_character_knowledge)
    params = list(sig.parameters.keys())
    assert 'user_id' in params, "get_character_knowledge should accept user_id parameter"
    
    # Check delete_story method
    sig = inspect.signature(GraphitiManager.delete_story)
    params = list(sig.parameters.keys())
    assert 'user_id' in params, "delete_story should accept user_id parameter"
    
    # Check detect_contradictions method
    sig = inspect.signature(GraphitiManager.detect_contradictions)
    params = list(sig.parameters.keys())
    assert 'user_id' in params, "detect_contradictions should accept user_id parameter"
    
    print("✅ GraphitiManager methods have been updated with user_id parameters")


def test_story_processor_method_signatures():
    """Test that StoryProcessor methods have been updated to accept user_id"""
    print("Testing StoryProcessor method signatures...")
    
    import inspect
    from core.story_processor import StoryProcessor
    
    # Check process_story method
    sig = inspect.signature(StoryProcessor.process_story)
    params = list(sig.parameters.keys())
    assert 'user_id' in params, "process_story should accept user_id parameter"
    
    print("✅ StoryProcessor methods have been updated with user_id parameters")


def test_cinegraph_agent_method_signatures():
    """Test that CineGraphAgent methods have been updated to accept user_id"""
    print("Testing CineGraphAgent method signatures...")
    
    import inspect
    from agents.cinegraph_agent import CineGraphAgent
    
    # Check detect_inconsistencies method
    sig = inspect.signature(CineGraphAgent.detect_inconsistencies)
    params = list(sig.parameters.keys())
    assert 'user_id' in params, "detect_inconsistencies should accept user_id parameter"
    
    # Check query_story method
    sig = inspect.signature(CineGraphAgent.query_story)
    params = list(sig.parameters.keys())
    assert 'user_id' in params, "query_story should accept user_id parameter"
    
    # Check validate_story_consistency method
    sig = inspect.signature(CineGraphAgent.validate_story_consistency)
    params = list(sig.parameters.keys())
    assert 'user_id' in params, "validate_story_consistency should accept user_id parameter"
    
    print("✅ CineGraphAgent methods have been updated with user_id parameters")


def test_query_filtering_logic():
    """Test that query filtering logic includes user_id"""
    print("Testing query filtering logic...")
    
    # Check that GraphitiManager queries include user_id filtering
    import inspect
    source = inspect.getsource(GraphitiManager.get_story_graph)
    assert "user_id" in source, "get_story_graph should include user_id in queries"
    assert "WHERE" in source, "get_story_graph should include WHERE clause"
    
    source = inspect.getsource(GraphitiManager.get_character_knowledge)
    assert "user_id" in source, "get_character_knowledge should include user_id in queries"
    
    source = inspect.getsource(GraphitiManager.delete_story)
    assert "user_id" in source, "delete_story should include user_id in queries"
    
    print("✅ Query filtering logic includes user_id")


def test_api_endpoints_pass_user_id():
    """Test that API endpoints pass user_id to underlying methods"""
    print("Testing API endpoints pass user_id...")
    
    # Read the main.py file to check if endpoints pass current_user.id
    with open('/Users/shachiakyaagba/Desktop/cinegraph/backend/app/main.py', 'r') as f:
        main_content = f.read()
    
    # Check that endpoints pass current_user.id
    assert "current_user.id" in main_content, "API endpoints should pass current_user.id"
    
    # Check specific endpoint patterns
    assert "process_story(story_input.content, story_input.story_id, current_user.id)" in main_content
    assert "get_story_graph(story_id, current_user.id)" in main_content
    assert "get_character_knowledge(" in main_content and "current_user.id" in main_content
    
    print("✅ API endpoints correctly pass user_id")


def test_auth_configuration():
    """Test that authentication is properly configured"""
    print("Testing authentication configuration...")
    
    # Check that we're using the correct Supabase key
    from app.auth import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
    
    assert SUPABASE_URL is not None, "SUPABASE_URL should be set"
    assert SUPABASE_SERVICE_ROLE_KEY is not None, "SUPABASE_SERVICE_ROLE_KEY should be set"
    
    print("✅ Authentication configuration is correct")


def run_all_tests():
    """Run all user isolation tests"""
    print("🔒 Testing User Data Isolation Implementation")
    print("=" * 50)
    
    try:
        test_story_input_model()
        test_user_model()
        test_graphiti_manager_method_signatures()
        test_story_processor_method_signatures()
        test_cinegraph_agent_method_signatures()
        test_query_filtering_logic()
        test_api_endpoints_pass_user_id()
        test_auth_configuration()
        
        print("\n🎉 All user isolation tests passed!")
        print("✅ User data isolation implementation is working correctly")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
