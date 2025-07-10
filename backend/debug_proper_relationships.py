#!/usr/bin/env python3
"""
Investigate proper Graphiti 0.3.0 relationship creation
"""

import asyncio
import time
from datetime import datetime
from core.graphiti_manager import GraphitiManager

async def debug_proper_relationships():
    """Debug proper relationship creation in Graphiti 0.3.0"""
    
    print("🔍 Investigating Proper Graphiti 0.3.0 Relationship Creation...")
    
    # Initialize GraphitiManager
    manager = GraphitiManager()
    
    try:
        # Connect to Graphiti
        await manager.connect()
        print("✅ Connected to Graphiti")
        
        # Clear any existing data for a clean test
        print("\n🧹 Checking current database state...")
        
        # Simple database overview
        overview_query = "MATCH (n) RETURN count(n) as node_count"
        overview_result = await manager.client.get_nodes_by_query(overview_query)
        print(f"Current nodes in database: {overview_result[0].get('node_count', 0) if overview_result else 0}")
        
        rel_overview_query = "MATCH ()-[r]->() RETURN count(r) as rel_count"
        rel_overview_result = await manager.client.get_nodes_by_query(rel_overview_query)
        print(f"Current relationships in database: {rel_overview_result[0].get('rel_count', 0) if rel_overview_result else 0}")
        
        # Test with a simple, clear story
        print("\n📝 Creating a simple story episode...")
        test_group_id = "test_proper_rels_001"
        
        episode_result = await manager.client.add_episode(
            name="Simple Relationship Test",
            episode_body="Alice found a golden key. The key opened a wooden door. Alice walked through the door into a garden.",
            source_description="Simple relationship test",
            reference_time=datetime.utcnow(),
            group_id=test_group_id
        )
        
        print(f"📊 Episode result: {episode_result}")
        
        # Wait a moment for processing
        print("⏳ Waiting for processing...")
        time.sleep(2)
        
        # Try building communities - this might be needed to commit relationships
        print("\n🏗️ Building communities to commit relationships...")
        try:
            await manager.client.build_communities()
            print("✅ Communities built successfully")
        except Exception as e:
            print(f"⚠️ Community building failed: {e}")
        
        # Check search results again
        print("\n🔍 Checking search results...")
        search_results = await manager.client.search(
            query="Alice found key door garden",
            group_ids=[test_group_id],
            num_results=10
        )
        
        print(f"📊 Search results count: {len(search_results)}")
        
        for i, result in enumerate(search_results):
            print(f"\n   Search Result {i+1}:")
            print(f"      Type: {type(result).__name__}")
            if hasattr(result, 'name'):
                print(f"      Name: {getattr(result, 'name', 'none')}")
            if hasattr(result, 'fact'):
                print(f"      Fact: {getattr(result, 'fact', 'none')}")
            if 'EntityEdge' in type(result).__name__:
                print(f"      Source: {getattr(result, 'source_node_uuid', 'none')}")
                print(f"      Target: {getattr(result, 'target_node_uuid', 'none')}")
        
        # Now check what's in Neo4j
        print("\n🔍 Checking Neo4j after community building...")
        
        # Node count
        nodes_after = await manager.client.get_nodes_by_query("MATCH (n) RETURN count(n) as count")
        print(f"Nodes after: {nodes_after[0].get('count', 0) if nodes_after else 0}")
        
        # Relationship count  
        rels_after = await manager.client.get_nodes_by_query("MATCH ()-[r]->() RETURN count(r) as count")
        print(f"Relationships after: {rels_after[0].get('count', 0) if rels_after else 0}")
        
        # Check relationship types
        rel_types = await manager.client.get_nodes_by_query("MATCH ()-[r]->() RETURN DISTINCT type(r) as rel_type, count(r) as count")
        print(f"Relationship types:")
        for rel in rel_types:
            print(f"   - {rel.get('rel_type', 'unknown')}: {rel.get('count', 0)}")
        
        # Sample some relationships with their properties
        sample_rels = await manager.client.get_nodes_by_query("""
            MATCH (a)-[r]->(b) 
            RETURN type(r) as rel_type, 
                   r.name as name_prop, 
                   r.fact as fact_prop,
                   a.name as source_name,
                   b.name as target_name
            LIMIT 5
        """)
        
        print(f"\nSample relationships:")
        for i, rel in enumerate(sample_rels):
            print(f"   {i+1}. {rel.get('rel_type', 'unknown')}")
            print(f"      From: {rel.get('source_name', 'unknown')} -> To: {rel.get('target_name', 'unknown')}")
            print(f"      Name property: {rel.get('name_prop', 'none')}")
            print(f"      Fact property: {rel.get('fact_prop', 'none')}")
        
        # Try retrieve_episodes to see if we're missing something
        print("\n🔍 Trying retrieve_episodes...")
        episodes = await manager.client.retrieve_episodes(
            reference_time=datetime.utcnow(),
            last_n=5,
            group_ids=[test_group_id]
        )
        
        print(f"Retrieved episodes: {len(episodes)}")
        for i, episode in enumerate(episodes):
            print(f"   Episode {i+1}: {type(episode).__name__}")
            if hasattr(episode, 'name'):
                print(f"      Name: {getattr(episode, 'name', 'none')}")
            if hasattr(episode, 'episode_body'):
                print(f"      Body: {getattr(episode, 'episode_body', 'none')[:100]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.close()

if __name__ == "__main__":
    asyncio.run(debug_proper_relationships())
