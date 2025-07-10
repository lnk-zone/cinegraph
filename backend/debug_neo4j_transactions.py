#!/usr/bin/env python3
"""
Test direct Neo4j transaction handling
"""

import asyncio
from core.graphiti_manager import GraphitiManager
from neo4j import AsyncGraphDatabase
import os

async def debug_neo4j_transactions():
    """Debug Neo4j transaction handling"""
    
    print("🔍 Debugging Neo4j Transaction Handling...")
    
    # Get Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI", os.getenv("GRAPHITI_DATABASE_URL"))
    neo4j_username = os.getenv("NEO4J_USERNAME", os.getenv("GRAPHITI_DATABASE_USER"))
    neo4j_password = os.getenv("NEO4J_PASSWORD", os.getenv("GRAPHITI_DATABASE_PASSWORD"))
    
    print(f"Neo4j URI: {neo4j_uri}")
    print(f"Neo4j Username: {neo4j_username}")
    
    # Test 1: Direct Neo4j connection
    print("\n📊 Test 1: Direct Neo4j Connection")
    try:
        driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        
        async with driver.session() as session:
            # Try a simple query
            result = await session.run("RETURN 1 as test")
            record = await result.single()
            print(f"   ✅ Direct connection works: {record['test']}")
            
            # Check current database state
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            print(f"   📊 Current nodes: {record['count']}")
            
            # Try to create a test node
            result = await session.run("""
                CREATE (t:TestNode {name: 'DirectNeo4jTest', created: datetime()})
                RETURN t.name as name
            """)
            record = await result.single()
            print(f"   ✅ Created test node: {record['name']}")
            
            # Check if it persisted
            result = await session.run("MATCH (t:TestNode) RETURN count(t) as count")
            record = await result.single()
            print(f"   📊 TestNode count: {record['count']}")
            
        await driver.close()
        
    except Exception as e:
        print(f"   ❌ Direct Neo4j connection failed: {e}")
    
    # Test 2: Graphiti connection and query handling
    print("\n📊 Test 2: Graphiti Connection Analysis")
    
    manager = GraphitiManager()
    try:
        await manager.connect()
        print("   ✅ Graphiti connected")
        
        # Check what database Graphiti is using
        if hasattr(manager.client, 'database'):
            print(f"   📊 Graphiti database: {manager.client.database}")
        
        # Check driver details
        if hasattr(manager.client, 'driver'):
            driver = manager.client.driver
            print(f"   📊 Driver type: {type(driver)}")
            if hasattr(driver, 'get_server_info'):
                try:
                    info = await driver.get_server_info()
                    print(f"   📊 Server info: {info}")
                except:
                    print("   📊 Server info not available")
        
        # Try to run a query through Graphiti that should definitely persist
        print("   🔍 Testing Graphiti query execution...")
        
        result = await manager.client.get_nodes_by_query("""
            CREATE (g:GraphitiTest {name: 'GraphitiDirectTest', created: datetime()})
            RETURN g.name as name
        """)
        print(f"   📊 Graphiti query result: {result}")
        
        # Immediately check if it's there
        check_result = await manager.client.get_nodes_by_query("""
            MATCH (g:GraphitiTest) 
            RETURN g.name as name, g.created as created
        """)
        print(f"   📊 Immediate check result: {check_result}")
        
        # Check total node count
        count_result = await manager.client.get_nodes_by_query("MATCH (n) RETURN count(n) as count")
        print(f"   📊 Total nodes via Graphiti: {count_result}")
        
    except Exception as e:
        print(f"   ❌ Graphiti testing failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.close()
    
    # Test 3: Check if it's a different database instance
    print("\n📊 Test 3: Re-check with fresh connection")
    
    try:
        driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        
        async with driver.session() as session:
            # Check for our test nodes
            result = await session.run("MATCH (t:TestNode) RETURN count(t) as test_nodes")
            record = await result.single()
            print(f"   📊 TestNode count (fresh): {record['test_nodes']}")
            
            result = await session.run("MATCH (g:GraphitiTest) RETURN count(g) as graphiti_nodes")
            record = await result.single()
            print(f"   📊 GraphitiTest count (fresh): {record['graphiti_nodes']}")
            
            # Show all labels
            result = await session.run("CALL db.labels()")
            labels = [record['label'] async for record in result]
            print(f"   📊 All node labels: {labels}")
            
            # Show all relationship types
            result = await session.run("CALL db.relationshipTypes()")
            rel_types = [record['relationshipType'] async for record in result]
            print(f"   📊 All relationship types: {rel_types}")
            
        await driver.close()
        
    except Exception as e:
        print(f"   ❌ Fresh connection check failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_neo4j_transactions())
