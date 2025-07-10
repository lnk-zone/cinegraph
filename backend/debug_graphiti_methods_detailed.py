#!/usr/bin/env python3
"""
Check all available Graphiti methods for committing data
"""

import asyncio
from datetime import datetime
from core.graphiti_manager import GraphitiManager
import inspect

async def debug_graphiti_methods_detailed():
    """Check all available methods in Graphiti 0.3.0"""
    
    print("🔍 Detailed Graphiti 0.3.0 Method Analysis...")
    
    # Initialize GraphitiManager
    manager = GraphitiManager()
    
    try:
        # Connect to Graphiti
        await manager.connect()
        print("✅ Connected to Graphiti")
        
        # Get all methods and their signatures
        client = manager.client
        all_methods = [method for method in dir(client) if not method.startswith('_')]
        
        print(f"\n📊 All available methods ({len(all_methods)}):")
        
        for method_name in sorted(all_methods):
            method = getattr(client, method_name)
            if callable(method):
                try:
                    sig = inspect.signature(method)
                    print(f"   {method_name}{sig}")
                    
                    # Check for docstring
                    if method.__doc__:
                        doc_lines = method.__doc__.strip().split('\n')
                        if doc_lines:
                            print(f"      └─ {doc_lines[0]}")
                except Exception:
                    print(f"   {method_name} (signature unavailable)")
            else:
                print(f"   {method_name} (property)")
        
        # Look for any methods that might commit or save data
        print(f"\n🔍 Looking for commit/save methods...")
        commit_keywords = ['commit', 'save', 'flush', 'persist', 'sync', 'write', 'store']
        
        for method_name in all_methods:
            if any(keyword in method_name.lower() for keyword in commit_keywords):
                method = getattr(client, method_name)
                print(f"   🎯 Found: {method_name}")
                if callable(method) and method.__doc__:
                    print(f"      └─ {method.__doc__.strip().split()[0] if method.__doc__ else 'No docs'}")
        
        # Check if there are any async methods we're missing
        print(f"\n🔍 Testing alternative approaches...")
        
        # Try to see if we can directly access the driver
        if hasattr(client, 'driver'):
            print("   📊 Client has 'driver' attribute")
            if hasattr(client.driver, 'close'):
                print("   📊 Driver has 'close' method")
        
        # Check if there's a database property
        if hasattr(client, 'database'):
            print("   📊 Client has 'database' attribute")
        
        # Try a simple node creation to see if we can bypass the episode system
        print(f"\n🔍 Testing direct node creation...")
        
        try:
            # Try to run a simple CREATE query to see if we can bypass Graphiti's caching
            test_query = """
            CREATE (a:TestEntity {name: 'DirectTest', created_at: datetime()})
            RETURN a.name as name
            """
            
            direct_result = await client.get_nodes_by_query(test_query)
            print(f"   ✅ Direct node creation worked: {direct_result}")
            
            # Check if it's now in the database
            check_query = "MATCH (n:TestEntity) RETURN count(n) as count"
            check_result = await client.get_nodes_by_query(check_query)
            print(f"   📊 TestEntity nodes in database: {check_result[0].get('count', 0) if check_result else 0}")
            
        except Exception as e:
            print(f"   ❌ Direct node creation failed: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.close()

if __name__ == "__main__":
    asyncio.run(debug_graphiti_methods_detailed())
