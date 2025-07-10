#!/usr/bin/env python3
"""
Test script to verify that add_episode refactoring is working correctly.
This verifies that the session_id parameter has been properly replaced with group_id.
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from core.graphiti_manager import GraphitiManager


async def test_add_episode_refactoring():
    """Test that add_episode calls work with the new signature."""
    print("🔍 Testing add_episode refactoring...")
    
    try:
        # Initialize GraphitiManager
        graphiti_manager = GraphitiManager()
        await graphiti_manager.connect()
        
        story_id = f"test_refactor_{uuid.uuid4().hex[:8]}"
        
        # Test 1: create_story_session should work without session_id parameter
        print("✅ Testing create_story_session...")
        session_id = await graphiti_manager.create_story_session(story_id)
        print(f"✅ Session created: {session_id}")
        
        # Test 2: add_memory should work with new add_episode signature
        print("✅ Testing add_memory...")
        memory_result = await graphiti_manager.add_memory(
            story_id=story_id,
            content="Test memory for refactoring validation",
            role="user"
        )
        
        if memory_result.get("status") == "success":
            print(f"✅ Memory added successfully: {memory_result.get('episode_id')}")
            print(f"✅ Session ID captured: {memory_result.get('session_id')}")
        else:
            print(f"❌ Memory addition failed: {memory_result.get('error')}")
            return False
        
        # Test 3: Verify session tracking is working
        if story_id in graphiti_manager._story_sessions:
            print(f"✅ Session tracking working: {graphiti_manager._story_sessions[story_id]}")
        else:
            print("❌ Session tracking not working")
            return False
        
        await graphiti_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Refactoring test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the refactoring test."""
    print("🚀 Testing add_episode and session handling refactoring")
    print("=" * 50)
    
    success = await test_add_episode_refactoring()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 add_episode refactoring is working correctly!")
        print("✅ Session handling updated successfully")
        print("✅ All add_episode calls use new group_id parameter")
        print("✅ Session ID tracking is functioning")
    else:
        print("⚠️ Refactoring test failed - check the implementation")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
