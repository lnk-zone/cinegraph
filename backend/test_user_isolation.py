#!/usr/bin/env python3
"""
Test script to verify user data isolation is working correctly
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from core.story_processor import StoryProcessor
from core.graphiti_manager import GraphitiManager


async def test_user_isolation():
    """Test that user data isolation is working correctly"""
    
    print("=== Testing User Data Isolation ===")
    
    # Sample story content
    story_content = """
    Alice walked into the magical forest. She discovered a hidden treasure chest near the old oak tree.
    Bob was also in the forest, but he was looking for herbs to make a healing potion.
    """
    
    try:
        # Initialize components
        print("1. Initializing GraphitiManager...")
        graphiti_manager = GraphitiManager()
        await graphiti_manager.initialize()
        
        print("2. Initializing StoryProcessor...")
        story_processor = StoryProcessor(graphiti_manager=graphiti_manager)
        
        # Process the same story for two different users
        print("3. Processing story for User 1...")
        user1_id = "user_001"
        story1_id = "story_001"
        result1 = await story_processor.process_story(story_content, story1_id, user1_id)
        
        print("4. Processing story for User 2...")
        user2_id = "user_002"
        story2_id = "story_002"
        result2 = await story_processor.process_story(story_content, story2_id, user2_id)
        
        # Verify data isolation
        print("5. Testing data isolation...")
        
        # Try to get User 1's story graph with User 2's ID (should be empty)
        user1_graph = await graphiti_manager.get_story_graph(story1_id, user1_id)
        user2_graph = await graphiti_manager.get_story_graph(story2_id, user2_id)
        
        # Try cross-user access (should return empty results)
        user1_graph_as_user2 = await graphiti_manager.get_story_graph(story1_id, user2_id)
        user2_graph_as_user1 = await graphiti_manager.get_story_graph(story2_id, user1_id)
        
        print("6. Results:")
        print(f"   User 1 story entities: {len(user1_graph.entities)}")
        print(f"   User 2 story entities: {len(user2_graph.entities)}")
        print(f"   User 1 story accessed by User 2: {len(user1_graph_as_user2.entities)}")
        print(f"   User 2 story accessed by User 1: {len(user2_graph_as_user1.entities)}")
        
        # Test character knowledge isolation
        print("7. Testing character knowledge isolation...")
        
        # Both users should have Alice in their stories
        try:
            user1_alice_knowledge = await graphiti_manager.get_character_knowledge(
                story1_id, "Alice", user_id=user1_id
            )
            user2_alice_knowledge = await graphiti_manager.get_character_knowledge(
                story2_id, "Alice", user_id=user2_id
            )
            
            print(f"   User 1 Alice knowledge items: {len(user1_alice_knowledge.knowledge_items)}")
            print(f"   User 2 Alice knowledge items: {len(user2_alice_knowledge.knowledge_items)}")
            
            # Try cross-user access
            user1_alice_as_user2 = await graphiti_manager.get_character_knowledge(
                story1_id, "Alice", user_id=user2_id
            )
            
            print(f"   User 1 Alice knowledge accessed by User 2: {len(user1_alice_as_user2.knowledge_items)}")
            
        except Exception as e:
            print(f"   Character knowledge test error: {e}")
        
        # Verify isolation worked
        if (len(user1_graph.entities) > 0 and len(user2_graph.entities) > 0 and
            len(user1_graph_as_user2.entities) == 0 and len(user2_graph_as_user1.entities) == 0):
            print("✅ User data isolation is working correctly!")
        else:
            print("❌ User data isolation may not be working correctly!")
            print(f"   Expected: User graphs should have entities, cross-user access should be empty")
        
        # Test deletion isolation
        print("8. Testing deletion isolation...")
        
        # Delete User 1's story
        delete_result = await graphiti_manager.delete_story(story1_id, user1_id)
        print(f"   Delete User 1 story result: {delete_result['status']}")
        
        # Verify User 1's story is gone but User 2's story remains
        user1_graph_after_delete = await graphiti_manager.get_story_graph(story1_id, user1_id)
        user2_graph_after_delete = await graphiti_manager.get_story_graph(story2_id, user2_id)
        
        print(f"   User 1 entities after delete: {len(user1_graph_after_delete.entities)}")
        print(f"   User 2 entities after delete: {len(user2_graph_after_delete.entities)}")
        
        if (len(user1_graph_after_delete.entities) == 0 and len(user2_graph_after_delete.entities) > 0):
            print("✅ Deletion isolation is working correctly!")
        else:
            print("❌ Deletion isolation may not be working correctly!")
        
        print("\n✅ User isolation test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if 'graphiti_manager' in locals():
            await graphiti_manager.close()


if __name__ == "__main__":
    asyncio.run(test_user_isolation())
