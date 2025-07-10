#!/usr/bin/env python3
"""
Smoke Test for Graphiti 0.3.0 Integration
=========================================

This script runs a minimal smoke test to verify that the Graphiti 0.3.0 
breaking changes have been properly addressed and the system can connect
and perform basic queries.
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime
from typing import Dict, Any

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from core.graphiti_manager import GraphitiManager
from core.story_processor import StoryProcessor
from graphiti_core.search.search import SearchConfig


async def test_graphiti_connection():
    """Test basic Graphiti connection and health check."""
    print("🔍 Testing Graphiti Connection...")
    
    try:
        # Initialize GraphitiManager
        graphiti_manager = GraphitiManager()
        
        # Test connection
        await graphiti_manager.connect()
        print("✅ Connection established successfully")
        
        # Test health check
        health_status = await graphiti_manager.health_check()
        print(f"✅ Health check status: {health_status['status']}")
        
        if health_status['status'] == 'healthy':
            print(f"   - Node count: {health_status.get('node_count', 'unknown')}")
            print(f"   - Database: {health_status.get('database_name', 'unknown')}")
        
        await graphiti_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False


async def test_search_config_imports():
    """Test that the new import paths work correctly."""
    print("\n🔍 Testing Search Config Imports...")
    
    try:
        # Test SearchConfig initialization with new signature
        session_id = "test_session_123"
        search_config = SearchConfig(
            group_ids=[session_id],
            search_methods=["cosine_similarity"],
            reranker="node_distance",
            num_episodes=5
        )
        print("✅ SearchConfig initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Search config test failed: {str(e)}")
        return False


async def test_story_processing():
    """Test basic story processing pipeline."""
    print("\n🔍 Testing Story Processing Pipeline...")
    
    try:
        # Initialize story processor
        story_processor = StoryProcessor()
        
        # Test story content
        test_story = """
        Alice walked into the mysterious forest. The old oak tree stood tall,
        its branches reaching toward the cloudy sky. She found a golden key
        near the tree's roots and wondered what it might unlock.
        """
        
        story_id = f"test_story_{uuid.uuid4().hex[:8]}"
        user_id = "test_user"
        
        # Process the story
        result = await story_processor.process_story(test_story, story_id, user_id)
        
        if "error" in result:
            print(f"❌ Story processing failed: {result['error']}")
            return False
        
        print("✅ Story processing completed successfully")
        print(f"   - Entities extracted: {len(result.get('entities', []))}")
        print(f"   - Relationships extracted: {len(result.get('relationships', []))}")
        print(f"   - Processing time: {result.get('metadata', {}).get('processing_time_ms', 'unknown')}ms")
        
        return True
        
    except Exception as e:
        print(f"❌ Story processing test failed: {str(e)}")
        return False


async def test_memory_operations():
    """Test memory operations using the GraphitiManager."""
    print("\n🔍 Testing Memory Operations...")
    
    try:
        graphiti_manager = GraphitiManager()
        await graphiti_manager.connect()
        
        story_id = f"memory_test_{uuid.uuid4().hex[:8]}"
        
        # Test adding memory
        memory_result = await graphiti_manager.add_memory(
            story_id=story_id,
            content="This is a test memory about Alice's adventure.",
            role="user"
        )
        
        if memory_result.get("status") == "success":
            print("✅ Memory added successfully")
            
            # Test retrieving memory
            memory_context = await graphiti_manager.get_memory(story_id, limit=5)
            print(f"✅ Memory retrieved: {len(memory_context) if memory_context else 0} characters")
            
        else:
            print(f"❌ Memory operation failed: {memory_result.get('error', 'unknown')}")
            return False
        
        await graphiti_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Memory operations test failed: {str(e)}")
        return False


async def test_search_operations():
    """Test search operations using the new SearchConfig."""
    print("\n🔍 Testing Search Operations...")
    
    try:
        graphiti_manager = GraphitiManager()
        await graphiti_manager.connect()
        
        story_id = f"search_test_{uuid.uuid4().hex[:8]}"
        
        # Add some content first
        await graphiti_manager.add_memory(
            story_id=story_id,
            content="Alice discovered a magical forest with talking animals.",
            role="user"
        )
        
        # Test search memory
        search_results = await graphiti_manager.search_memory(
            story_id=story_id,
            query="Alice forest",
            limit=3
        )
        
        print(f"✅ Search completed: {len(search_results)} results found")
        
        await graphiti_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Search operations test failed: {str(e)}")
        return False


async def run_smoke_tests():
    """Run all smoke tests."""
    print("🚀 Starting Graphiti 0.3.0 Smoke Tests")
    print("=" * 50)
    
    test_results = []
    
    # Test 1: Connection
    test_results.append(await test_graphiti_connection())
    
    # Test 2: Import paths
    test_results.append(await test_search_config_imports())
    
    # Test 3: Story processing
    test_results.append(await test_story_processing())
    
    # Test 4: Memory operations
    test_results.append(await test_memory_operations())
    
    # Test 5: Search operations
    test_results.append(await test_search_operations())
    
    # Summary
    print("\n" + "=" * 50)
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All smoke tests passed! Graphiti 0.3.0 integration is working correctly.")
        return True
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please check the configuration.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_smoke_tests())
    sys.exit(0 if success else 1)
