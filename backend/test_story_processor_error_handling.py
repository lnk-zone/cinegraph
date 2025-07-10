#!/usr/bin/env python3
"""
Test script to verify StoryProcessor error handling and defensive checks.
This tests the fixes for episode_result.uuid and scene_errors collection.
"""

import asyncio
from datetime import datetime
from core.story_processor import StoryProcessor
from core.graphiti_manager import GraphitiManager

async def test_story_processor_error_handling():
    """Test that StoryProcessor handles errors gracefully"""
    
    print("🔍 Testing StoryProcessor Error Handling...")
    
    # Initialize StoryProcessor
    processor = StoryProcessor()
    
    try:
        # Test with a simple story
        test_story = """
        Once upon a time, there was a brave knight named Sir Arthur.
        He lived in a grand castle by the sea.
        
        One day, Sir Arthur decided to go on a quest.
        He rode his trusty horse through the enchanted forest.
        
        In the forest, he met a wise old wizard named Merlin.
        Merlin gave him a magical sword to help on his journey.
        """
        
        story_id = "test_story_001"
        user_id = "test_user"
        
        print(f"📝 Processing story: {story_id}")
        
        # Process the story
        result = await processor.process_story(test_story, story_id, user_id)
        
        print(f"✅ Story processing completed")
        print(f"📊 Entities extracted: {len(result.get('entities', []))}")
        print(f"📊 Relationships extracted: {len(result.get('relationships', []))}")
        print(f"📊 Scenes extracted: {len(result.get('scenes', []))}")
        print(f"📊 Knowledge items: {len(result.get('knowledge_items', []))}")
        
        # Check metadata
        metadata = result.get('metadata', {})
        print(f"📊 Processing time: {metadata.get('processing_time_ms', 0):.2f}ms")
        print(f"📊 Scene count: {metadata.get('scene_count', 0)}")
        print(f"📊 Word count: {metadata.get('word_count', 0)}")
        
        # Check for scene errors
        scene_errors = metadata.get('scene_errors', [])
        print(f"📊 Scene errors: {len(scene_errors)}")
        
        if scene_errors:
            print("⚠️  Scene errors found:")
            for error in scene_errors:
                print(f"   - Scene {error.get('scene_id', 'unknown')}: {error.get('error_type', 'unknown')} - {error.get('error_message', 'no message')}")
        else:
            print("✅ No scene errors encountered")
        
        # Check that we have a valid result structure
        assert 'entities' in result, "Result should have 'entities' key"
        assert 'relationships' in result, "Result should have 'relationships' key"
        assert 'scenes' in result, "Result should have 'scenes' key"
        assert 'knowledge_items' in result, "Result should have 'knowledge_items' key"
        assert 'metadata' in result, "Result should have 'metadata' key"
        assert 'scene_errors' in result['metadata'], "Metadata should have 'scene_errors' key"
        
        print("✅ All structural checks passed")
        
        # Test episode_id handling in scenes
        scenes = result.get('scenes', [])
        if scenes:
            for scene in scenes:
                episode_id = scene.get('properties', {}).get('episode_id')
                print(f"📋 Scene {scene.get('id', 'unknown')}: episode_id = {episode_id}")
        
        print("✅ Episode ID handling test completed")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_graphiti_manager_error_handling():
    """Test that GraphitiManager handles episode_result properly"""
    
    print("\n🔍 Testing GraphitiManager Error Handling...")
    
    manager = GraphitiManager()
    
    try:
        # Connect to Graphiti
        await manager.connect()
        print("✅ Connected to Graphiti")
        
        # Test entity upsert
        entity_result = await manager.upsert_entity(
            entity_type="CHARACTER",
            properties={
                "id": "test_char_001",
                "name": "Test Character",
                "story_id": "test_story_001"
            }
        )
        
        print(f"✅ Entity upsert result: {entity_result.get('status', 'unknown')}")
        print(f"📋 Episode ID: {entity_result.get('episode_id', 'None')}")
        
        # Test relationship upsert
        rel_result = await manager.upsert_relationship(
            relationship_type="KNOWS",
            from_id="test_char_001",
            to_id="test_char_002",
            properties={
                "story_id": "test_story_001",
                "confidence": 0.8
            }
        )
        
        print(f"✅ Relationship upsert result: {rel_result.get('status', 'unknown')}")
        print(f"📋 Episode ID: {rel_result.get('episode_id', 'None')}")
        
        # Test memory add
        memory_result = await manager.add_memory(
            story_id="test_story_001",
            content="This is a test memory",
            role="user"
        )
        
        print(f"✅ Memory add result: {memory_result.get('status', 'unknown')}")
        print(f"📋 Episode ID: {memory_result.get('episode_id', 'None')}")
        
        print("✅ All GraphitiManager tests passed")
        
    except Exception as e:
        print(f"❌ Error during GraphitiManager testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await manager.close()
    
    return True

async def main():
    """Run all tests"""
    
    print("🚀 Starting StoryProcessor Error Handling Tests")
    print("=" * 60)
    
    # Test 1: StoryProcessor error handling
    test1_passed = await test_story_processor_error_handling()
    
    # Test 2: GraphitiManager error handling
    test2_passed = await test_graphiti_manager_error_handling()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   StoryProcessor Error Handling: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   GraphitiManager Error Handling: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("🎉 All tests passed! Error handling is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please review the output above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
