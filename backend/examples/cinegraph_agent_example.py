"""
CineGraphAgent Usage Example
============================

This example demonstrates how to use the CineGraphAgent with OpenAI SDK integration
for story analysis, inconsistency detection, and temporal querying.
"""

import asyncio
import json
from agents.agent_factory import create_cinegraph_agent, initialize_cinegraph_agent
from core.redis_alerts import alert_manager


async def main():
    """Main example function demonstrating CineGraphAgent usage."""
    
    print("🎬 CineGraphAgent Integration Example")
    print("="*50)
    
    # Create and initialize the agent
    print("\n1. Creating CineGraphAgent...")
    try:
        agent = create_cinegraph_agent()
        agent = await initialize_cinegraph_agent(agent)
        print("✅ CineGraphAgent initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return
    
    # Health check
    print("\n2. Performing health check...")
    health = await agent.health_check()
    print(f"Status: {health['status']}")
    if health['status'] == 'healthy':
        print("✅ All components are healthy")
        for component, status in health['components'].items():
            print(f"  - {component}: {status}")
    else:
        print(f"❌ Health check failed: {health.get('error', 'Unknown error')}")
    
    # Example story content
    story_content = """
    Chapter 1: The Discovery
    
    Sarah found the ancient map in her grandmother's attic on a rainy Tuesday morning. 
    The map showed a hidden treasure location deep in the Amazon rainforest. 
    She immediately called her best friend Marcus to share the discovery.
    
    Chapter 2: The Journey Begins
    
    Three days later, Sarah and Marcus met at the airport. They had packed their 
    expedition gear and were ready for adventure. Sarah brought the map, carefully 
    wrapped in protective cloth.
    
    Chapter 3: The Contradiction
    
    Upon arriving in Brazil, Marcus mentioned he had seen the map before - his 
    grandfather had shown him the same map last year. This confused Sarah, as she 
    was certain the map had been locked away in her grandmother's attic for decades.
    """
    
    extracted_data = {
        "story_id": "example_story_001",
        "entities": [
            {"name": "Sarah", "type": "CHARACTER", "role": "protagonist"},
            {"name": "Marcus", "type": "CHARACTER", "role": "friend"},
            {"name": "Grandmother's Attic", "type": "LOCATION"},
            {"name": "Amazon Rainforest", "type": "LOCATION"},
            {"name": "Ancient Map", "type": "ITEM", "significance": "treasure_map"}
        ],
        "relationships": [
            {"type": "FRIENDSHIP", "from": "Sarah", "to": "Marcus"},
            {"type": "OWNS", "from": "Sarah", "to": "Ancient Map"},
            {"type": "LOCATED_AT", "from": "Ancient Map", "to": "Grandmother's Attic"}
        ]
    }
    
    # 3. Story Analysis
    print("\n3. Analyzing story content...")
    try:
        analysis = await agent.analyze_story(story_content, extracted_data)
        print("✅ Story analysis completed")
        print(f"Analysis result: {json.dumps(analysis, indent=2)}")
    except Exception as e:
        print(f"❌ Story analysis failed: {e}")
    
    # 4. Inconsistency Detection
    print("\n4. Detecting inconsistencies...")
    try:
        inconsistencies = await agent.detect_inconsistencies("example_story_001")
        print("✅ Inconsistency detection completed")
        print(f"Inconsistencies found: {json.dumps(inconsistencies, indent=2)}")
    except Exception as e:
        print(f"❌ Inconsistency detection failed: {e}")
    
    # 5. Story Querying
    print("\n5. Querying story...")
    questions = [
        "Who found the ancient map?",
        "Where was the map discovered?",
        "What did Marcus know about the map?",
        "What is the main inconsistency in this story?"
    ]
    
    for question in questions:
        try:
            print(f"\nQ: {question}")
            response = await agent.query_story("example_story_001", question)
            print(f"A: {response.get('answer', 'No answer available')}")
        except Exception as e:
            print(f"❌ Query failed: {e}")
    
    # 6. Story Consistency Validation
    print("\n6. Validating story consistency...")
    try:
        validation = await agent.validate_story_consistency("example_story_001")
        print("✅ Story consistency validation completed")
        print(f"Validation report: {json.dumps(validation, indent=2)}")
    except Exception as e:
        print(f"❌ Story consistency validation failed: {e}")
    
    # 7. Demonstrate Redis Alert Handling
    print("\n7. Testing Redis alert handling...")
    try:
        # Simulate a contradiction alert
        test_alert = {
            "id": "test_alert_001",
            "story_id": "example_story_001",
            "alert_type": "contradiction_detected",
            "from": "Sarah's claim about map origin",
            "to": "Marcus's claim about seeing the map before",
            "reason": "Conflicting information about map's previous exposure",
            "detected_at": "2024-01-15T10:30:00Z",
            "severity": "high"
        }
        
        # Publish the alert
        alert_manager.publish_alert(test_alert)
        print("✅ Test alert published to Redis")
        
        # Wait a moment for the alert to be processed
        await asyncio.sleep(2)
        
    except Exception as e:
        print(f"❌ Redis alert test failed: {e}")
    
    print("\n" + "="*50)
    print("🎬 CineGraphAgent Integration Example Completed")


async def demonstrate_temporal_queries():
    """Demonstrate temporal querying capabilities."""
    
    print("\n🕐 Temporal Query Examples")
    print("="*30)
    
    agent = await initialize_cinegraph_agent(create_cinegraph_agent())
    
    # Example temporal queries
    temporal_questions = [
        "What did Sarah know about the map when she first found it?",
        "What information did Marcus have about the map before the trip?",
        "What contradictions emerged during the story timeline?",
        "What events happened before the contradiction was discovered?"
    ]
    
    for question in temporal_questions:
        try:
            print(f"\nTemporal Q: {question}")
            response = await agent.query_story("example_story_001", question)
            print(f"A: {response.get('answer', 'No answer available')}")
        except Exception as e:
            print(f"❌ Temporal query failed: {e}")


async def demonstrate_few_shot_examples():
    """Demonstrate few-shot learning examples for the agent."""
    
    print("\n🎯 Few-Shot Learning Examples")
    print("="*35)
    
    # These examples would typically be included in the system prompt
    # to improve the agent's performance on similar tasks
    
    few_shot_examples = [
        {
            "query": "What did character X know at time Y?",
            "cypher": "MATCH (c:Character {name: 'X'})-[knows:KNOWS]->(k:Knowledge) WHERE k.valid_from <= 'Y' AND (k.valid_to IS NULL OR k.valid_to >= 'Y') RETURN k",
            "explanation": "This query finds all knowledge that character X had at time Y by checking temporal validity"
        },
        {
            "query": "Find temporal contradictions in story",
            "cypher": "MATCH (e1:Event)-[:OCCURRED_AT]->(t1:Time), (e2:Event)-[:OCCURRED_AT]->(t2:Time) WHERE t1.timestamp > t2.timestamp AND e1.requires_knowledge_from = e2.id RETURN e1, e2",
            "explanation": "This query finds events that occur before their prerequisites"
        },
        {
            "query": "Detect character knowledge inconsistencies",
            "cypher": "MATCH (c:Character)-[k1:KNOWS]->(info1), (c)-[k2:KNOWS]->(info2) WHERE k1.contradicts = k2.id RETURN c, info1, info2",
            "explanation": "This query finds contradictory knowledge held by the same character"
        }
    ]
    
    print("Few-shot examples for improved agent performance:")
    for example in few_shot_examples:
        print(f"\nQuery Type: {example['query']}")
        print(f"Cypher: {example['cypher']}")
        print(f"Explanation: {example['explanation']}")


if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())
    
    # Run additional demonstrations
    asyncio.run(demonstrate_temporal_queries())
    asyncio.run(demonstrate_few_shot_examples())
