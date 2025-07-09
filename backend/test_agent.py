#!/usr/bin/env python3
"""
Simple test script for CineGraphAgent
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_agent():
    """Test the CineGraphAgent functionality"""
    
    print("🧪 Testing CineGraphAgent Integration")
    print("=" * 50)
    
    # Check if required environment variables are set
    required_vars = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY", "NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file")
        return
    
    try:
        from agents.agent_factory import create_cinegraph_agent, initialize_cinegraph_agent
        
        # Create agent
        print("1. Creating CineGraphAgent...")
        agent = create_cinegraph_agent()
        print("✅ Agent created successfully")
        
        # Initialize agent
        print("2. Initializing agent...")
        agent = await initialize_cinegraph_agent(agent)
        print("✅ Agent initialized successfully")
        
        # Health check
        print("3. Performing health check...")
        health = await agent.health_check()
        print(f"Status: {health['status']}")
        
        if health['status'] == 'healthy':
            print("✅ All components are healthy:")
            for component, status in health.get('components', {}).items():
                print(f"  - {component}: {status}")
        else:
            print(f"❌ Health check failed: {health.get('error', 'Unknown error')}")
            
        # Test basic functionality
        print("\n4. Testing basic functionality...")
        
        # Test story analysis
        story_content = """
        Sarah found an ancient map in her grandmother's attic. The map showed a treasure location.
        Later, Marcus said he had seen the same map before, which confused Sarah.
        """
        
        extracted_data = {
            "story_id": "test_story_001",
            "entities": [
                {"name": "Sarah", "type": "CHARACTER"},
                {"name": "Marcus", "type": "CHARACTER"},
                {"name": "Ancient Map", "type": "ITEM"}
            ],
            "relationships": [
                {"type": "FRIENDSHIP", "from": "Sarah", "to": "Marcus"}
            ]
        }
        
        print("   Testing story analysis...")
        analysis = await agent.analyze_story(story_content, extracted_data)
        
        if "error" in analysis:
            print(f"   ❌ Story analysis failed: {analysis['error']}")
        else:
            print("   ✅ Story analysis completed successfully")
            
        # Test story querying
        print("   Testing story querying...")
        query_result = await agent.query_story("test_story_001", "Who found the map?")
        
        if "error" in query_result:
            print(f"   ❌ Story query failed: {query_result['error']}")
        else:
            print("   ✅ Story query completed successfully")
            
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent())
