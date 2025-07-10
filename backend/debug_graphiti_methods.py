#!/usr/bin/env python3
"""
Debug script to check what methods are available in Graphiti 0.3.0
"""

import asyncio
from datetime import datetime
from core.graphiti_manager import GraphitiManager

async def debug_graphiti_methods():
    """Debug available methods in Graphiti 0.3.0"""
    
    print("🔍 Debugging Graphiti 0.3.0 available methods...")
    
    # Initialize GraphitiManager
    manager = GraphitiManager()
    
    try:
        # Connect to Graphiti
        await manager.connect()
        print("✅ Connected to Graphiti")
        
        # Print all available methods
        print(f"📊 Graphiti Client Type: {type(manager.client)}")
        print(f"📊 Available methods: {[method for method in dir(manager.client) if not method.startswith('_')]}")
        
        # Check specific methods we're interested in
        methods_to_check = [
            'extract_facts',
            'get_summary', 
            'add_episode',
            'search',
            'retrieve_episodes',
            'get_nodes_by_query',
            'build_communities',
            'build_indices_and_constraints'
        ]
        
        print("\n📋 Method availability check:")
        for method in methods_to_check:
            available = hasattr(manager.client, method)
            print(f"   {method}: {'✅' if available else '❌'}")
            
            if available:
                method_obj = getattr(manager.client, method)
                print(f"      - Callable: {'✅' if callable(method_obj) else '❌'}")
                if hasattr(method_obj, '__doc__') and method_obj.__doc__:
                    print(f"      - Doc: {method_obj.__doc__[:100]}...")
        
        # Test what we can extract from search results
        print("\n🔍 Testing data extraction from search...")
        
        # Create a test episode
        episode_result = await manager.client.add_episode(
            name="Test Episode for Data Extraction",
            episode_body="Alice walked through the magical forest. She met a wise wizard named Gandalf who gave her a magical ring.",
            source_description="Test extraction",
            reference_time=datetime.utcnow(),
            group_id="test_extraction"
        )
        
        print(f"📊 Episode created: {episode_result}")
        
        # Now search for it
        search_results = await manager.client.search(
            query="Alice forest wizard",
            group_ids=["test_extraction"],
            num_results=5
        )
        
        print(f"📊 Search results count: {len(search_results)}")
        
        for i, result in enumerate(search_results):
            print(f"   Result {i+1}:")
            print(f"      Type: {type(result)}")
            print(f"      Attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
            
            # Check for common attributes
            common_attrs = ['episode_body', 'content', 'entities', 'relationships', 'facts']
            for attr in common_attrs:
                if hasattr(result, attr):
                    value = getattr(result, attr)
                    print(f"      {attr}: {value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.close()

if __name__ == "__main__":
    asyncio.run(debug_graphiti_methods())
