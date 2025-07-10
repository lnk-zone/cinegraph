#!/usr/bin/env python3
"""
Debug script to check the structure of episode_result from Graphiti
"""

import asyncio
from datetime import datetime
from core.graphiti_manager import GraphitiManager

async def debug_episode_structure():
    """Debug the structure of episode_result from Graphiti"""
    
    print("🔍 Debugging episode_result structure...")
    
    # Initialize GraphitiManager
    manager = GraphitiManager()
    
    try:
        # Connect to Graphiti
        await manager.connect()
        print("✅ Connected to Graphiti")
        
        # Create a test episode
        episode_result = await manager.client.add_episode(
            name="Debug Episode",
            episode_body="This is a test episode to debug the structure",
            source_description="Debug test",
            reference_time=datetime.utcnow(),
            group_id="debug_session"
        )
        
        print(f"📊 Episode Result Type: {type(episode_result)}")
        print(f"📊 Episode Result Attributes: {dir(episode_result)}")
        
        # Check for common attributes
        attributes_to_check = ['uuid', 'id', 'group_id', 'created_at', 'name', 'episode_body']
        
        for attr in attributes_to_check:
            if hasattr(episode_result, attr):
                value = getattr(episode_result, attr)
                print(f"✅ {attr}: {value} (type: {type(value)})")
            else:
                print(f"❌ {attr}: NOT FOUND")
        
        # Print the actual object representation
        print(f"📋 Full object: {episode_result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if manager.client:
            await manager.client.close()

if __name__ == "__main__":
    asyncio.run(debug_episode_structure())
