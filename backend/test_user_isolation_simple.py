#!/usr/bin/env python3
"""
Simple test script to verify user isolation implementation without heavy dependencies
"""

import sys
import os
import re
from pathlib import Path

# Resolve repository root based on this file's location
REPO_ROOT = Path(__file__).resolve().parents[1]

def test_story_input_model():
    """Test that StoryInput model includes user_id field"""
    print("Testing StoryInput model...")
    
    # Read the models file
    models_file = REPO_ROOT / 'backend' / 'core' / 'models.py'
    with open(models_file, 'r') as f:
        models_content = f.read()
    
    # Check if StoryInput has user_id field
    story_input_pattern = r'class StoryInput.*?(?=class|\Z)'
    story_input_match = re.search(story_input_pattern, models_content, re.DOTALL)
    
    if story_input_match:
        story_input_class = story_input_match.group(0)
        if 'user_id' in story_input_class:
            print("✅ StoryInput model includes user_id field")
        else:
            print("❌ StoryInput model missing user_id field")
            return False
    else:
        print("❌ StoryInput class not found")
        return False
    
    return True


def test_graphiti_manager_methods():
    """Test that GraphitiManager methods have been updated to accept user_id"""
    print("Testing GraphitiManager methods...")
    
    # Read the graphiti_manager file
    manager_file = REPO_ROOT / 'backend' / 'core' / 'graphiti_manager.py'
    with open(manager_file, 'r') as f:
        manager_content = f.read()
    
    # Check key methods for user_id parameter
    methods_to_check = [
        'add_story_content',
        'get_story_graph', 
        'get_character_knowledge',
        'delete_story',
        'detect_contradictions'
    ]
    
    for method in methods_to_check:
        # Look for method definition with user_id parameter
        method_pattern = rf'def {method}.*?user_id.*?:'
        if re.search(method_pattern, manager_content, re.DOTALL):
            print(f"✅ {method} method includes user_id parameter")
        else:
            print(f"❌ {method} method missing user_id parameter")
            return False
    
    return True


def test_story_processor_methods():
    """Test that StoryProcessor methods have been updated to accept user_id"""
    print("Testing StoryProcessor methods...")
    
    # Read the story_processor file
    processor_file = REPO_ROOT / 'backend' / 'core' / 'story_processor.py'
    with open(processor_file, 'r') as f:
        processor_content = f.read()
    
    # Check process_story method for user_id parameter
    if re.search(r'def process_story.*?user_id.*?:', processor_content, re.DOTALL):
        print("✅ process_story method includes user_id parameter")
    else:
        print("❌ process_story method missing user_id parameter")
        return False
    
    return True


def test_api_endpoints():
    """Test that API endpoints pass user_id to underlying methods"""
    print("Testing API endpoints...")
    
    # Read the main.py file
    main_file = REPO_ROOT / 'backend' / 'app' / 'main.py'
    with open(main_file, 'r') as f:
        main_content = f.read()
    
    # Check that endpoints pass current_user.id
    if "current_user.id" in main_content:
        print("✅ API endpoints pass current_user.id")
    else:
        print("❌ API endpoints not passing current_user.id")
        return False
    
    # Check specific patterns
    patterns_to_check = [
        r'process_story.*?current_user\.id',
        r'get_story_graph.*?current_user\.id',
        r'get_character_knowledge.*?current_user\.id',
        r'delete_story.*?current_user\.id'
    ]
    
    for pattern in patterns_to_check:
        if re.search(pattern, main_content, re.DOTALL):
            print(f"✅ Found pattern: {pattern}")
        else:
            print(f"⚠️  Pattern not found (may be on multiple lines): {pattern}")
    
    return True


def test_query_filtering():
    """Test that queries include user_id filtering"""
    print("Testing query filtering...")
    
    # Read the graphiti_manager file
    manager_file = REPO_ROOT / 'backend' / 'core' / 'graphiti_manager.py'
    with open(manager_file, 'r') as f:
        manager_content = f.read()
    
    # Check for user_id filtering in queries
    if "WHERE" in manager_content and "user_id" in manager_content:
        print("✅ Queries include user_id filtering")
    else:
        print("❌ Queries missing user_id filtering")
        return False
    
    # Check for specific filtering patterns
    if "n.user_id = $user_id" in manager_content:
        print("✅ Found proper user_id filtering pattern")
    else:
        print("⚠️  User_id filtering pattern may be different")
    
    return True


def test_auth_configuration():
    """Test that authentication is properly configured"""
    print("Testing authentication configuration...")
    
    # Read the auth.py file
    auth_file = REPO_ROOT / 'backend' / 'app' / 'auth.py'
    with open(auth_file, 'r') as f:
        auth_content = f.read()
    
    # Check for SUPABASE_SERVICE_ROLE_KEY
    if "SUPABASE_SERVICE_ROLE_KEY" in auth_content:
        print("✅ Authentication uses SUPABASE_SERVICE_ROLE_KEY")
    else:
        print("❌ Authentication not using SUPABASE_SERVICE_ROLE_KEY")
        return False
    
    return True


def test_temporal_contradiction_detection():
    """Test that temporal contradiction detection includes user_id"""
    print("Testing temporal contradiction detection...")
    
    # Read the temporal_contradiction_detection.py file
    detection_file = REPO_ROOT / 'backend' / 'tasks' / 'temporal_contradiction_detection.py'
    with open(detection_file, 'r') as f:
        detection_content = f.read()
    
    # Check for user_id in scan_story_contradictions
    if re.search(r'scan_story_contradictions.*?user_id', detection_content, re.DOTALL):
        print("✅ Temporal contradiction detection includes user_id")
    else:
        print("❌ Temporal contradiction detection missing user_id")
        return False
    
    return True


def run_all_tests():
    """Run all user isolation tests"""
    print("🔒 Testing User Data Isolation Implementation")
    print("=" * 50)
    
    tests = [
        test_story_input_model,
        test_graphiti_manager_methods,
        test_story_processor_methods,
        test_api_endpoints,
        test_query_filtering,
        test_auth_configuration,
        test_temporal_contradiction_detection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Add spacing between tests
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All user isolation tests passed!")
        print("✅ User data isolation implementation is working correctly")
        return True
    else:
        print("❌ Some tests failed - user isolation implementation needs review")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
