#!/usr/bin/env python3
"""
Test script for the story ingestion pipeline
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from core.story_processor import StoryProcessor
from core.graphiti_manager import GraphitiManager


async def test_story_ingestion():
    """Test the story ingestion pipeline"""
    
    # Sample story content (around 300 words)
    test_story = """
    The young hero John stepped into the ancient forest, his magical sword gleaming in the moonlight. 
    The forest was dark and mysterious, filled with strange sounds and glowing eyes peering from behind 
    the ancient oak trees.

    As he ventured deeper, John encountered a wise old wizard named Merlin who lived in a small cottage 
    near the crystal lake. Merlin told John about the evil dragon that had been terrorizing the nearby 
    village of Oakenheart for months.

    "The dragon's lair is hidden deep within the Crystal Caves," Merlin explained, handing John a 
    magical potion. "This will protect you from the dragon's fire breath. But beware - the dragon 
    is cunning and powerful."

    John thanked the wizard and continued his journey. Along the way, he met a brave knight named 
    Sir Marcus who was also seeking to defeat the dragon. Together, they traveled to the Crystal Caves, 
    where an epic battle awaited them.

    The dragon emerged from its lair, breathing fire and roaring loudly. John and Sir Marcus fought 
    bravely, using their combined skills to defeat the mighty beast. The village of Oakenheart was 
    finally safe.
    """
    
    print("=== Testing Story Ingestion Pipeline ===")
    print(f"Story length: {len(test_story)} characters ({len(test_story.split())} words)")
    print()
    
    try:
        # Initialize components
        print("1. Initializing GraphitiManager...")
        graphiti_manager = GraphitiManager()
        await graphiti_manager.initialize()
        
        print("2. Initializing StoryProcessor...")
        story_processor = StoryProcessor(graphiti_manager=graphiti_manager)
        
        # Process the story
        print("3. Processing story content...")
        start_time = datetime.utcnow()
        
        story_id = "test_story_001"
        user_id = "test_user_001"
        result = await story_processor.process_story(test_story, story_id, user_id)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        print(f"4. Processing completed in {processing_time:.2f}ms")
        
        # Check if we met the performance target
        if processing_time < 300:
            print("✅ Performance target met (<300ms)")
        else:
            print("⚠️  Performance target not met (>300ms)")
        
        # Display results
        print("\n=== Extraction Results ===")
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        print(f"Entities found: {len(result.get('entities', []))}")
        print(f"Relationships found: {len(result.get('relationships', []))}")
        print(f"Scenes created: {len(result.get('scenes', []))}")
        print(f"Knowledge items: {len(result.get('knowledge_items', []))}")
        
        # Show sample entities
        print("\n=== Sample Entities ===")
        for i, entity in enumerate(result.get('entities', [])[:5]):
            print(f"{i+1}. {entity['name']} ({entity['type']})")
        
        # Show sample relationships
        print("\n=== Sample Relationships ===")
        for i, rel in enumerate(result.get('relationships', [])[:5]):
            print(f"{i+1}. {rel['type']}: {rel['from_id']} -> {rel['to_id']}")
        
        # Show traceability mappings
        print("\n=== Traceability Mappings ===")
        mappings = result.get('traceability_mappings', {})
        for segment_id, scene_id in list(mappings.items())[:3]:
            print(f"{segment_id} -> {scene_id}")
        
        # Show processing stats
        print("\n=== Processing Statistics ===")
        stats = story_processor.get_processing_stats()
        print(f"Total processed: {stats['total_processed']}")
        print(f"Average processing time: {stats['avg_processing_time']:.2f}ms")
        print(f"Last processed: {stats['last_processed']}")
        
        # Test traceability lookup
        print("\n=== Testing Traceability Lookup ===")
        test_segment = "segment_1"
        scene_id = story_processor.get_traceability_mapping(test_segment)
        print(f"Mapping for {test_segment}: {scene_id}")
        
        print("\n✅ Story ingestion pipeline test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if 'graphiti_manager' in locals():
            await graphiti_manager.close()


if __name__ == "__main__":
    asyncio.run(test_story_ingestion())
