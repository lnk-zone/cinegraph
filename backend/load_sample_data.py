#!/usr/bin/env python3
"""
Load Sample Data Script
=======================

This script loads sample data including Items and OWNS relations using
Graphiti's episodic memory system.

Usage:
    python load_sample_data.py
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(__file__))

from core.graphiti_manager import GraphitiManager
from core.models import ItemEntity, Ownership, ItemType, TransferMethod


async def load_sample_data():
    """Load sample data including Items and OWNS relations."""
    
    print("Loading sample data with Items and OWNS relations...")
    
    # Initialize GraphitiManager
    manager = GraphitiManager()
    await manager.initialize()
    
    try:
        story_id = "sample_story_001"
        user_id = "test_user_001"
        
        # Create sample characters
        characters = [
            {
                "id": "char_001",
                "name": "Alice",
                "description": "A brave knight on a quest",
                "story_id": story_id,
                "user_id": user_id
            },
            {
                "id": "char_002", 
                "name": "Bob",
                "description": "A wise wizard with ancient knowledge",
                "story_id": story_id,
                "user_id": user_id
            },
            {
                "id": "char_003",
                "name": "Charlie",
                "description": "A cunning thief with nimble fingers",
                "story_id": story_id,
                "user_id": user_id
            }
        ]
        
        # Create sample items
        items = [
            ItemEntity(
                id="item_001",
                type=ItemType.WEAPON,
                name="Excalibur",
                description="Legendary sword of immense power",
                origin_scene="scene_001",
                current_owner="char_001"
            ),
            ItemEntity(
                id="item_002",
                type=ItemType.ARTIFACT,
                name="Crystal of Wisdom",
                description="A mystical crystal that glows with inner light",
                origin_scene="scene_002",
                current_owner="char_002"
            ),
            ItemEntity(
                id="item_003",
                type=ItemType.TOOL,
                name="Lockpicking Set",
                description="A set of fine tools for opening locked doors",
                origin_scene="scene_003",
                current_owner="char_003"
            ),
            ItemEntity(
                id="item_004",
                type=ItemType.CLOTHING,
                name="Cloak of Invisibility",
                description="A cloak that renders the wearer invisible",
                origin_scene="scene_001",
                current_owner=None  # No current owner
            )
        ]
        
        # Create sample ownership relationships
        ownerships = [
            Ownership(
                from_id="char_001",
                to_id="item_001",
                ownership_start=datetime(2024, 1, 1, 10, 0, 0),
                transfer_method=TransferMethod.INHERITANCE,
                ownership_notes="Inherited from father"
            ),
            Ownership(
                from_id="char_002",
                to_id="item_002",
                ownership_start=datetime(2024, 1, 15, 14, 30, 0),
                transfer_method=TransferMethod.GIFT,
                ownership_notes="Received as a gift from the ancient order"
            ),
            Ownership(
                from_id="char_003",
                to_id="item_003",
                ownership_start=datetime(2024, 2, 1, 9, 15, 0),
                transfer_method=TransferMethod.EXCHANGE,
                ownership_notes="Traded for information"
            ),
            # Previous ownership that ended
            Ownership(
                from_id="char_001",
                to_id="item_004",
                ownership_start=datetime(2024, 1, 5, 16, 0, 0),
                ownership_end=datetime(2024, 2, 10, 11, 30, 0),
                transfer_method=TransferMethod.THEFT,
                ownership_notes="Lost during a battle"
            )
        ]
        
        # Add characters to episodic memory
        print("\nAdding characters...")
        for char in characters:
            result = await manager.upsert_entity("Character", char)
            print(f"Added character: {char['name']} - {result['status']}")
        
        # Add items to episodic memory  
        print("\nAdding items...")
        for item in items:
            item_data = {
                "id": item.id,
                "name": item.name,
                "type": item.type.value,
                "description": item.description,
                "origin_scene": item.origin_scene,
                "current_owner": item.current_owner,
                "is_active": item.is_active,
                "story_id": story_id,
                "user_id": user_id
            }
            result = await manager.upsert_entity("Item", item_data)
            print(f"Added item: {item.name} - {result['status']}")
        
        # Add ownership relationships
        print("\nAdding ownership relationships...")
        for ownership in ownerships:
            ownership_data = {
                "from_id": ownership.from_id,
                "to_id": ownership.to_id,
                "ownership_start": ownership.ownership_start.isoformat(),
                "ownership_end": ownership.ownership_end.isoformat() if ownership.ownership_end else None,
                "transfer_method": ownership.transfer_method.value,
                "ownership_notes": ownership.ownership_notes,
                "story_id": story_id,
                "user_id": user_id
            }
            result = await manager.upsert_relationship("OWNS", ownership.from_id, ownership.to_id, ownership_data)
            print(f"Added ownership: {ownership.from_id} -> {ownership.to_id} - {result['status']}")
        
        # Add some sample story content that references these items and relationships
        print("\nAdding story episode...")
        story_content = """
        In the ancient kingdom, three heroes embarked on a quest. Alice wielded the legendary Excalibur, 
        inherited from her father, a blade that shone with righteous light. Bob carried the Crystal of Wisdom, 
        a gift from the ancient order that pulsed with mystical energy. Charlie kept his lockpicking set close, 
        tools he had traded valuable information to acquire.
        
        Alice had once possessed a Cloak of Invisibility, but it was lost during a fierce battle with shadow creatures.
        Now the cloak lies somewhere in the forgotten ruins, waiting for a new owner to claim it.
        
        The heroes knew that their items were more than mere objects - they were extensions of their very souls,
        each with a history and purpose that would shape their destiny.
        """
        
        story_result = await manager.add_memory(
            story_id=story_id,
            content=story_content,
            role="system",
            metadata={"type": "sample_data", "contains_items": True, "contains_ownership": True}
        )
        print(f"Added story episode - {story_result['status']}")
        
        # Verify the data was added by searching
        print("\nVerifying data...")
        search_results = await manager.search_memory(story_id, "Excalibur sword Alice", limit=5)
        print(f"Search results for 'Excalibur sword Alice': {len(search_results)} results found")
        
        ownership_results = await manager.search_memory(story_id, "ownership inherited gift", limit=5)
        print(f"Search results for 'ownership inherited gift': {len(ownership_results)} results found")
        
        # Get statistics
        stats = await manager.get_query_statistics()
        print(f"\nDatabase statistics:")
        print(f"- Total episodes: {stats.get('total_episodes', 'unknown')}")
        print(f"- Story count: {stats.get('story_count', 'unknown')}")
        print(f"- Active sessions: {len(stats.get('active_sessions', []))}")
        
        print(f"\n✅ Sample data loaded successfully!")
        print(f"Story ID: {story_id}")
        print(f"Characters: {len(characters)}")
        print(f"Items: {len(items)}")
        print(f"Ownership relationships: {len(ownerships)}")
        
    except Exception as e:
        print(f"❌ Error loading sample data: {e}")
        raise
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(load_sample_data())
