#!/usr/bin/env python3
"""
Test script for StoryProcessor enhancements
Tests the new NLP features, scene segmentation, and continuity detection
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.story_processor import StoryProcessor
from core.graphiti_manager import GraphitiManager

# Sample story content for testing
SAMPLE_STORY = """
Chapter 1: The Beginning

I woke up in a strange place. The room was dark and I couldn't remember how I got there. Fear gripped my heart as I realized I was completely alone.

Meanwhile, in another part of the city, Sarah was having coffee with her friend Mark. They were discussing the mysterious disappearances that had been happening lately.

Chapter 2: The Discovery

Hours later, I found a hidden door behind the bookshelf. As I had predicted earlier, this house held many secrets. The corridor beyond was filled with ancient symbols.

Sarah received a call from the police. Another person had gone missing - someone she knew. Little did she know that this case would change everything.

***

The final confrontation was intense. I remembered what my grandmother had told me years ago about the old mansion. Everything was connected - the disappearances, the symbols, the dreams I'd been having.

Sarah and I finally met at the mansion. The truth was more terrifying than either of us had imagined.
"""

async def test_story_processor():
    """Test the enhanced StoryProcessor functionality"""
    
    print("🧪 Testing Enhanced StoryProcessor...")
    
    # Initialize processor (without OpenAI for this test)
    processor = StoryProcessor()
    
    # Test scene splitting with enhanced metadata
    print("\n📖 Testing scene splitting and metadata extraction...")
    scenes = processor._split_into_scenes(SAMPLE_STORY)
    
    print(f"Found {len(scenes)} scenes")
    for i, scene in enumerate(scenes):
        print(f"\nScene {i+1}:")
        print(f"  Chapter: {scene['chapter']}, Episode: {scene['episode']}")
        print(f"  POV: {scene['pov']['type']} (confidence: {scene['pov']['confidence']:.2f})")
        print(f"  Story Arc: {scene['story_arc']['primary_arc']} (intensity: {scene['story_arc']['intensity']})")
        print(f"  Chapter Boundary: {scene['chapter_boundary']['is_new_chapter']}")
        print(f"  Episode Boundary: {scene['episode_boundary']['is_new_episode']}")
        print(f"  Text Preview: {scene['text'][:100]}...")
    
    # Test mood and significance analysis
    print("\n🎭 Testing mood and significance analysis...")
    enhanced_scenes = await processor._analyze_mood_and_significance(scenes)
    
    for i, scene in enumerate(enhanced_scenes):
        mood = scene.get('mood', {})
        significance = scene.get('significance', {})
        print(f"\nScene {i+1} Analysis:")
        print(f"  Mood: {mood.get('primary_mood', 'unknown')} (intensity: {mood.get('intensity', 0):.2f})")
        print(f"  Significance: {significance.get('significance_score', 0):.2f}")
        print(f"  Key Terms: {significance.get('key_terms', [])}")
    
    # Test continuity detection
    print("\n🔗 Testing continuity detection...")
    continuity_edges = processor._detect_continuity_callbacks(enhanced_scenes)
    
    print(f"Found {len(continuity_edges)} continuity edges:")
    for edge in continuity_edges:
        print(f"  {edge['from_scene_id']} -> {edge['to_scene_id']}")
        print(f"    Phrase: '{edge['properties']['callback_phrase']}'")
        print(f"    Confidence: {edge['properties']['confidence']:.2f}")
        print(f"    Pattern: {edge['properties']['pattern_type']}")
    
    # Test full processing pipeline (without Graphiti connection)
    print("\n⚙️ Testing processing statistics...")
    print(f"Processing stats: {processor.get_processing_stats()}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_story_processor())
