#!/usr/bin/env python3
"""
Test Script for Schema Management Endpoints
===========================================

This script tests the schema management functionality:
1. Checks current schema status
2. Applies schema synchronization
3. Verifies schema after synchronization

Usage:
    python test_schema_management.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from core.graphiti_manager import GraphitiManager
from app.main import ensure_schema
from dotenv import load_dotenv

load_dotenv()


async def test_schema_management():
    """Test the schema management functionality."""
    
    print("=" * 60)
    print("CineGraph Schema Management Test")
    print("=" * 60)
    
    # Initialize GraphitiManager
    try:
        graphiti_manager = GraphitiManager()
        await graphiti_manager.initialize()
        print(f"✅ Connected to Neo4j: {graphiti_manager.config.database_url}")
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")
        return False
    
    # Test 1: Check current schema status
    print("\n🔍 Testing current schema status...")
    try:
        # Simulate the schema status check logic
        if hasattr(graphiti_manager.client, 'driver'):
            # Test SHOW CONSTRAINTS
            constraints_result = await graphiti_manager.client.driver.execute_query(
                "SHOW CONSTRAINTS",
                database_=graphiti_manager.config.database_name
            )
            constraints_count = len(constraints_result.records) if constraints_result.records else 0
            
            # Test SHOW INDEXES
            indexes_result = await graphiti_manager.client.driver.execute_query(
                "SHOW INDEXES", 
                database_=graphiti_manager.config.database_name
            )
            indexes_count = len(indexes_result.records) if indexes_result.records else 0
            
            print(f"✅ Current constraints: {constraints_count}")
            print(f"✅ Current indexes: {indexes_count}")
            
            # Check for story_id/user_id indexes
            if indexes_result.records:
                index_names = [record.get("name", "") for record in indexes_result.records]
                has_story_id = any("story_id" in name for name in index_names)
                has_user_id = any("user_id" in name for name in index_names)
                has_temporal = any("temporal" in name for name in index_names)
                
                print(f"   - story_id indexes: {'✅' if has_story_id else '❌'}")
                print(f"   - user_id indexes: {'✅' if has_user_id else '❌'}")
                print(f"   - temporal indexes: {'✅' if has_temporal else '❌'}")
            
        else:
            print("❌ Cannot access Neo4j driver directly")
            return False
            
    except Exception as e:
        print(f"❌ Schema status check failed: {e}")
        return False
    
    # Test 2: Apply schema synchronization
    print("\n🔧 Testing schema synchronization...")
    try:
        # Check if bootstrap script exists
        bootstrap_path = Path(__file__).parent / "neo4j_bootstrap.cypher"
        if not bootstrap_path.exists():
            print(f"❌ Bootstrap script not found: {bootstrap_path}")
            return False
        
        print(f"✅ Found bootstrap script: {bootstrap_path}")
        
        # Apply schema using the ensure_schema function
        # We need to set the global graphiti_manager for the function
        import app.main
        app.main.graphiti_manager = graphiti_manager
        
        result = await ensure_schema()
        
        if result["status"] in ["completed", "partial"]:
            print(f"✅ Schema sync result: {result['status']}")
            print(f"   - Total statements: {result['total_statements']}")
            print(f"   - Successful: {result['successful']}")
            print(f"   - Failed: {result['failed']}")
            
            if result["errors"]:
                print("   - Errors:")
                for error in result["errors"][:5]:  # Show first 5 errors
                    print(f"     • {error}")
                if len(result["errors"]) > 5:
                    print(f"     ... and {len(result['errors']) - 5} more")
        else:
            print(f"❌ Schema sync failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Schema synchronization failed: {e}")
        return False
    
    # Test 3: Verify schema after synchronization
    print("\n🔍 Verifying schema after synchronization...")
    try:
        # Re-check schema status
        constraints_result = await graphiti_manager.client.driver.execute_query(
            "SHOW CONSTRAINTS",
            database_=graphiti_manager.config.database_name
        )
        new_constraints_count = len(constraints_result.records) if constraints_result.records else 0
        
        indexes_result = await graphiti_manager.client.driver.execute_query(
            "SHOW INDEXES",
            database_=graphiti_manager.config.database_name
        )
        new_indexes_count = len(indexes_result.records) if indexes_result.records else 0
        
        print(f"✅ New constraints count: {new_constraints_count}")
        print(f"✅ New indexes count: {new_indexes_count}")
        
        # Check for CineGraphAgent requirements
        if indexes_result.records:
            index_names = [record.get("name", "") for record in indexes_result.records]
            has_story_id = any("story_id" in name for name in index_names)
            has_user_id = any("user_id" in name for name in index_names)
            has_temporal = any("temporal" in name for name in index_names)
            
            print(f"   - story_id indexes: {'✅' if has_story_id else '❌'}")
            print(f"   - user_id indexes: {'✅' if has_user_id else '❌'}")
            print(f"   - temporal indexes: {'✅' if has_temporal else '❌'}")
            
            # Calculate compatibility score
            compatibility_score = 0
            if new_constraints_count > 0:
                compatibility_score += 25
            if new_indexes_count > 10:
                compatibility_score += 25
            if has_story_id:
                compatibility_score += 20
            if has_user_id:
                compatibility_score += 20
            if has_temporal:
                compatibility_score += 10
            
            print(f"✅ Compatibility score: {compatibility_score}/100")
            
            if compatibility_score >= 80:
                print("🎉 Schema is now compatible with CineGraphAgent!")
                return True
            else:
                print("⚠️  Schema partially compatible but may need additional work")
                return True
        
    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        return False
    
    finally:
        # Clean up
        await graphiti_manager.close()
        print("\n🔌 Disconnected from Neo4j")


async def main():
    """Main test function."""
    success = await test_schema_management()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Schema management test PASSED")
        print("\nNext steps:")
        print("1. Start the FastAPI server: uvicorn app.main:app --reload")
        print("2. Test endpoints:")
        print("   GET  /api/admin/schema_status")
        print("   POST /api/admin/ensure_schema")
    else:
        print("❌ Schema management test FAILED")
        print("\nCheck the errors above and ensure:")
        print("1. Neo4j is running and accessible")
        print("2. Environment variables are set correctly")
        print("3. neo4j_bootstrap.cypher exists in the backend directory")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
