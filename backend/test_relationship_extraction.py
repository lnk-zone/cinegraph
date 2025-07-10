#!/usr/bin/env python3
"""
Test script for relationship extraction functionality.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from agents.cinegraph_agent import CineGraphAgent, DialoguePatternExtractor, InteractionStrengthExtractor, SNARelationshipExtractor
from core.graphiti_manager import GraphitiManager


class MockSearchResult:
    """Mock search result for testing."""
    def __init__(self, episode_body, created_at=None):
        self.episode_body = episode_body
        self.created_at = created_at or "2024-01-01T00:00:00Z"


class MockGraphitiClient:
    """Mock GraphitiManager client for testing."""
    async def search(self, query, group_ids=None, num_results=10):
        # Return mock search results with dialogue content
        mock_results = [
            MockSearchResult("Story Content: Alice said hello to Bob. They talked about the weather."),
            MockSearchResult("Story Content: Bob replied to Alice and mentioned Charlie was coming."),
            MockSearchResult("Story Content: Charlie arrived and greeted both Alice and Bob warmly."),
            MockSearchResult("Story Content: Alice, Bob, and Charlie discussed their plans together."),
        ]
        return mock_results


class MockGraphitiManager:
    """Mock GraphitiManager for testing."""
    def __init__(self):
        self.client = MockGraphitiClient()
        self._story_sessions = {"test_movie": "session_123"}


async def test_extractor_classes():
    """Test the individual extractor classes."""
    print("Testing extractor classes...")
    
    # Test DialoguePatternExtractor
    mock_results = [
        MockSearchResult("Story Content: Alice said hello to Bob. They talked about the weather."),
        MockSearchResult("Story Content: Bob replied to Alice and mentioned Charlie was coming."),
        MockSearchResult("Story Content: Charlie arrived and greeted both Alice and Bob warmly."),
    ]
    
    dialogue_extractor = DialoguePatternExtractor(mock_results)
    patterns = dialogue_extractor.extract_patterns()
    print(f"Extracted {len(patterns)} dialogue patterns")
    
    # Test InteractionStrengthExtractor
    interaction_extractor = InteractionStrengthExtractor(patterns)
    strengths = interaction_extractor.calculate_strengths()
    print(f"Calculated strengths for {len(strengths)} character pairs")
    
    # Test SNARelationshipExtractor
    sna_extractor = SNARelationshipExtractor(strengths)
    relationships = sna_extractor.generate_sna_relationships()
    print(f"Generated {len(relationships)} SNA relationships")
    
    # Show some example relationships
    for i, rel in enumerate(relationships[:3]):
        print(f"Relationship {i+1}: {rel['from_character']} -> {rel['to_character']} ({rel['type']}, strength: {rel['strength']})")
    
    return True


async def test_discover_relationships():
    """Test the full discover_relationships method."""
    print("\nTesting discover_relationships method...")
    
    # Create agent with mock GraphitiManager
    mock_manager = MockGraphitiManager()
    agent = CineGraphAgent(graphiti_manager=mock_manager)
    
    # Test relationship discovery
    result = await agent.discover_relationships("test_movie", "test_user")
    
    print(f"Discovery result status: {result['status']}")
    print(f"Relationships discovered: {result['relationships_discovered']}")
    print(f"Cypher queries generated: {len(result['cypher_queries'])}")
    
    # Show example Cypher query
    if result['cypher_queries']:
        print("\nExample Cypher query:")
        print(result['cypher_queries'][0])
    
    # Show SNA metrics
    if 'sna_metrics' in result:
        print(f"\nSNA Metrics:")
        print(f"  Total interactions: {result['sna_metrics']['total_interactions']}")
        print(f"  Unique character pairs: {result['sna_metrics']['unique_character_pairs']}")
        print(f"  Avg interaction strength: {result['sna_metrics']['avg_interaction_strength']:.2f}")
    
    return result['status'] == 'success'


async def main():
    """Run all tests."""
    print("Testing Enhanced Relationship Extraction in CineGraphAgent")
    print("=" * 60)
    
    try:
        # Test extractor classes
        extractor_test = await test_extractor_classes()
        
        # Test discover_relationships method
        discovery_test = await test_discover_relationships()
        
        print("\n" + "=" * 60)
        print("Test Results:")
        print(f"  Extractor classes: {'PASS' if extractor_test else 'FAIL'}")
        print(f"  Discover relationships: {'PASS' if discovery_test else 'FAIL'}")
        
        if extractor_test and discovery_test:
            print("\n✅ All tests passed! Enhanced relationship extraction is working correctly.")
        else:
            print("\n❌ Some tests failed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
