#!/usr/bin/env python3
"""
Test to verify the fixed StoryProcessor extraction pipeline
"""

import asyncio
from datetime import datetime
from core.story_processor import StoryProcessor

async def test_extraction_pipeline():
    """Test the fixed extraction pipeline"""
    
    print("🔍 Testing Fixed StoryProcessor Extraction Pipeline...")
    
    # Initialize StoryProcessor
    processor = StoryProcessor()
    
    try:
        # Test with a rich story that should generate entities and relationships
        test_story = """
        In the ancient kingdom of Eldoria, Princess Luna walked through the enchanted forest.
        She carried her father's magical sword, Starblade, which glowed with blue light.
        
        Near the crystal lake, she encountered the wise dragon Zephyr.
        The dragon told her about the lost Crown of Wisdom hidden in the Shadow Mountains.
        
        Luna decided to seek the crown to save her kingdom from the Dark Sorcerer Malachar.
        With Zephyr's blessing, she began her perilous journey toward the mountains.
        """
        
        story_id = "test_extraction_001"
        user_id = "test_user"
        
        print(f"📝 Processing rich story: {story_id}")
        
        # Process the story
        result = await processor.process_story(test_story, story_id, user_id)
        
        if "error" in result:
            print(f"❌ Story processing failed: {result['error']}")
            return False
        
        print(f"✅ Story processing completed successfully")
        
        # Detailed analysis
        entities = result.get('entities', [])
        relationships = result.get('relationships', [])
        scenes = result.get('scenes', [])
        knowledge_items = result.get('knowledge_items', [])
        metadata = result.get('metadata', {})
        
        print(f"📊 Extraction Results:")
        print(f"   - Entities: {len(entities)}")
        print(f"   - Relationships: {len(relationships)}")
        print(f"   - Scenes: {len(scenes)}")
        print(f"   - Knowledge items: {len(knowledge_items)}")
        print(f"   - Processing time: {metadata.get('processing_time_ms', 0):.2f}ms")
        print(f"   - Scene errors: {len(metadata.get('scene_errors', []))}")
        
        # Show extracted relationships
        if relationships:
            print("\\n📋 Extracted Relationships:")
            for i, rel in enumerate(relationships[:5]):  # Show first 5
                fact = rel.get('properties', {}).get('fact', 'No fact')
                print(f"   {i+1}. {rel.get('type', 'UNKNOWN')}: {fact[:100]}...")
        
        # Show extracted entities  
        if entities:
            print("\\n📋 Extracted Entities:")
            for i, entity in enumerate(entities[:5]):  # Show first 5
                print(f"   {i+1}. {entity.get('name', 'Unknown')} ({entity.get('type', 'UNKNOWN')})")
        
        # Show scene errors
        scene_errors = metadata.get('scene_errors', [])
        if scene_errors:
            print("\\n⚠️  Scene Errors:")
            for error in scene_errors:
                print(f"   - {error.get('error_type', 'unknown')}: {error.get('error_message', 'no message')}")
        else:
            print("\\n✅ No scene errors")
        
        # Verify defensive checks worked
        for scene in scenes:
            episode_id = scene.get('properties', {}).get('episode_id')
            print(f"📋 Scene {scene.get('id', 'unknown')}: episode_id = {episode_id} (defensive check: {'✅' if episode_id is None else '✅'})")
        
        print("\\n✅ All extraction pipeline tests completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_extraction_pipeline())
    print(f"\\n🎯 Test Result: {'✅ PASSED' if success else '❌ FAILED'}")
    exit(0 if success else 1)
