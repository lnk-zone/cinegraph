#!/usr/bin/env python3
"""
Test for refactored StoryProcessor with CinegraphAgent integration
"""

import asyncio
import sys
import os

# Mock CinegraphAgent for testing without OpenAI
class MockCinegraphAgent:
    """Mock CinegraphAgent for testing"""
    
    def __init__(self):
        self.openai_client = None  # No OpenAI client for testing
    
    async def analyze_scenes(self, scenes, story_id, user_id):
        """Mock scene analysis"""
        enhanced_scenes = []
        
        for i, scene in enumerate(scenes):
            # Add mock AI analysis
            enhanced_scene = {
                **scene,
                "chapter": 1 if i < 3 else 2,  # Simple chapter detection
                "episode": i + 1,
                "pov": {"type": "first_person" if "I" in scene["text"] else "third_person", "confidence": 0.8},
                "mood": {"primary_mood": "mysterious" if "secret" in scene["text"].lower() else "neutral", "intensity": 0.6},
                "story_arc": {"primary_arc": "exposition" if i == 0 else ("climax" if i == len(scenes)-1 else "rising_action"), "intensity": 0.7},
                "significance": {"score": 0.8 if i in [0, len(scenes)-1] else 0.6},
                "ai_analysis": {
                    "characters": ["protagonist", "Sarah"] if "Sarah" in scene["text"] else ["protagonist"],
                    "locations": ["mansion"] if "mansion" in scene["text"] else ["unknown"],
                    "themes": ["mystery", "fear"],
                    "continuity_references": ["earlier event"] if "remember" in scene["text"] else []
                }
            }
            enhanced_scenes.append(enhanced_scene)
        
        return {
            "entities": [{"id": "char_1", "name": "Protagonist", "type": "CHARACTER"}],
            "relationships": [{"from": "char_1", "to": "location_1", "type": "PRESENT_IN"}],
            "scenes": enhanced_scenes,
            "knowledge_items": [{"id": "know_1", "content": "Secret discovered", "type": "KNOWLEDGE"}],
            "continuity_edges": [{"from_scene": scenes[0]["id"], "to_scene": scenes[-1]["id"], "type": "CALLBACK"}],
            "processing_method": "ai_enhanced",
            "model_used": "mock-gpt-4"
        }

# Mock GraphitiManager
class MockGraphitiManager:
    """Mock GraphitiManager for testing"""
    
    def __init__(self):
        pass
    
    async def upsert_entity(self, entity_type, properties):
        return {"status": "success", "entity_id": properties.get("id")}
    
    async def upsert_relationship(self, relationship_type, from_id, to_id, properties):
        return {"status": "success", "relationship_id": f"{from_id}_{to_id}"}

# Test story content
SAMPLE_STORY = """
Chapter 1: The Beginning

I woke up in a strange place. The room was dark and I couldn't remember how I got there. Fear gripped my heart as I realized I was completely alone.

Meanwhile, in another part of the city, Sarah was having coffee with her friend Mark. They were discussing the mysterious disappearances that had been happening lately.

The final confrontation was intense. I remembered what my grandmother had told me years ago about the old mansion. Everything was connected.

Sarah and I finally met at the mansion. The truth was more terrifying than either of us had imagined.
"""

async def test_refactored_processor():
    """Test the refactored StoryProcessor"""
    
    print("🧪 Testing Refactored StoryProcessor with CinegraphAgent...")
    
    # Import StoryProcessor locally to avoid import issues
    from core.story_processor import StoryProcessor
    
    # Create mock dependencies
    mock_agent = MockCinegraphAgent()
    mock_manager = MockGraphitiManager()
    
    # Initialize processor with mocks
    processor = StoryProcessor(
        graphiti_manager=mock_manager,
        cinegraph_agent=mock_agent
    )
    
    # Test scene splitting
    print("\n📖 Testing basic scene splitting...")
    scenes = processor._split_into_scenes(SAMPLE_STORY)
    print(f"Found {len(scenes)} scenes")
    
    for i, scene in enumerate(scenes):
        print(f"  Scene {i+1}: {scene['word_count']} words")
        print(f"    Preview: {scene['text'][:50]}...")
    
    # Test agent-based processing
    print("\n🤖 Testing agent-based processing...")
    agent_results = await processor._process_with_agent(scenes, "test_story", "test_user")
    
    print(f"Processing method: {agent_results.get('processing_method')}")
    print(f"Model used: {agent_results.get('model_used')}")
    print(f"Enhanced scenes: {len(agent_results.get('scenes', []))}")
    print(f"Entities found: {len(agent_results.get('entities', []))}")
    print(f"Relationships found: {len(agent_results.get('relationships', []))}")
    print(f"Continuity edges: {len(agent_results.get('continuity_edges', []))}")
    
    # Show enhanced scene analysis
    print("\n📊 Enhanced Scene Analysis:")
    for i, scene in enumerate(agent_results.get('scenes', [])[:2]):  # Show first 2
        print(f"Scene {i+1}:")
        print(f"  Chapter: {scene.get('chapter')}, Episode: {scene.get('episode')}")
        print(f"  POV: {scene.get('pov', {}).get('type')} (confidence: {scene.get('pov', {}).get('confidence', 0):.2f})")
        print(f"  Mood: {scene.get('mood', {}).get('primary_mood')} (intensity: {scene.get('mood', {}).get('intensity', 0):.2f})")
        print(f"  Story Arc: {scene.get('story_arc', {}).get('primary_arc')}")
        print(f"  Significance: {scene.get('significance', {}).get('score', 0):.2f}")
        
        ai_analysis = scene.get('ai_analysis', {})
        print(f"  Characters: {ai_analysis.get('characters', [])}")
        print(f"  Locations: {ai_analysis.get('locations', [])}")
        print(f"  Themes: {ai_analysis.get('themes', [])}")
        print()
    
    # Test fallback without agent
    print("\n🔄 Testing fallback without agent...")
    processor_no_agent = StoryProcessor(graphiti_manager=mock_manager)
    
    # This should trigger the fallback path
    try:
        fallback_results = await processor_no_agent._process_with_agent(scenes, "test_story", "test_user")
        print("❌ Fallback test failed - should have raised an error")
    except AttributeError:
        print("✅ Fallback correctly handled missing agent")
    
    print("\n✅ All refactored processor tests completed!")

if __name__ == "__main__":
    asyncio.run(test_refactored_processor())
