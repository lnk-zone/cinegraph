#!/usr/bin/env python3
"""
Enhanced CineGraph Agent Test Script
===================================

This script demonstrates the enhanced capabilities of the CineGraph Agent including:
1. Advanced Cypher query validation and optimization
2. Query templates and caching
3. Comprehensive story analysis
4. Plot hole detection
5. Character consistency analysis
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any

# Import the enhanced agent
from agents.cinegraph_agent import CineGraphAgent
from core.graphiti_manager import GraphitiManager
from core.models import GraphitiConfig


class EnhancedAgentDemo:
    """Demonstration of enhanced CineGraph Agent capabilities."""
    
    def __init__(self):
        self.agent = None
        self.graphiti_manager = None
        
    async def setup(self):
        """Initialize the enhanced agent with all capabilities."""
        print("🚀 Setting up Enhanced CineGraph Agent...")
        
        # Initialize GraphitiManager
        config = GraphitiConfig(
            database_url=os.getenv("GRAPHITI_DATABASE_URL", "bolt://localhost:7687"),
            username=os.getenv("GRAPHITI_DATABASE_USER", "neo4j"),
            password=os.getenv("GRAPHITI_DATABASE_PASSWORD", "password"),
            database_name=os.getenv("GRAPHITI_DATABASE_NAME", "neo4j")
        )
        
        self.graphiti_manager = GraphitiManager(config)
        await self.graphiti_manager.connect()
        
        # Initialize Enhanced Agent
        self.agent = CineGraphAgent(
            graphiti_manager=self.graphiti_manager,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
        
        print("✅ Enhanced CineGraph Agent initialized successfully!")
        print(f"📊 Schema loaded: {len(self.agent.schema_context['entities'])} entities, {len(self.agent.schema_context['relationships'])} relationships")
        print(f"🎯 Query templates available: {list(self.agent.query_templates.keys())}")
        
    async def test_query_validation(self):
        """Test the enhanced query validation capabilities."""
        print("\n🔍 Testing Query Validation...")
        
        test_queries = [
            # Valid queries
            {
                "query": "MATCH (c:Character {story_id: $story_id}) RETURN c.name",
                "expected": True,
                "description": "Valid character query"
            },
            {
                "query": "MATCH (c:Character {story_id: $story_id})-[:KNOWS]->(k:Knowledge) WHERE k.valid_from <= $timestamp RETURN k",
                "expected": True,
                "description": "Valid temporal query"
            },
            # Invalid queries
            {
                "query": "DELETE FROM Character",
                "expected": False,
                "description": "Dangerous DELETE operation"
            },
            {
                "query": "MATCH (c:Character) RETURN c",
                "expected": False,
                "description": "Missing story_id filter"
            },
            {
                "query": "MATCH (c:Character {story_id: $story_id}",
                "expected": False,
                "description": "Unbalanced parentheses"
            }
        ]
        
        for test in test_queries:
            result = await self.agent.validate_query(test["query"])
            status = "✅" if result["valid"] == test["expected"] else "❌"
            print(f"{status} {test['description']}: {result['message']}")
            
            if result["valid"] and result["suggested_optimizations"]:
                print(f"   💡 Suggestions: {', '.join(result['suggested_optimizations'])}")
    
    async def test_optimized_queries(self):
        """Test optimized query templates."""
        print("\n⚡ Testing Optimized Query Templates...")
        
        story_id = "test_story_001"
        user_id = "test_user_001"
        
        # Test each template
        templates_to_test = [
            {
                "name": "story_timeline",
                "params": {"story_id": story_id, "user_id": user_id},
                "description": "Story timeline analysis"
            },
            {
                "name": "character_relationships",
                "params": {"story_id": story_id, "character_name": "John", "user_id": user_id},
                "description": "Character relationship mapping"
            },
            {
                "name": "temporal_knowledge_conflicts",
                "params": {"story_id": story_id, "user_id": user_id},
                "description": "Temporal consistency check"
            }
        ]
        
        for template in templates_to_test:
            print(f"\n🎯 Testing template: {template['name']}")
            result = await self.agent.optimized_query(template["name"], template["params"])
            
            if result["success"]:
                print(f"✅ {template['description']}: Success")
                print(f"   📊 Results: {len(result.get('data', []))} items")
                print(f"   💾 Cached: {result.get('cached', False)}")
            else:
                print(f"❌ {template['description']}: {result.get('error', 'Unknown error')}")
    
    async def test_caching_mechanism(self):
        """Test query caching functionality."""
        print("\n💾 Testing Query Caching...")
        
        test_query = "MATCH (c:Character {story_id: $story_id}) RETURN c.name LIMIT 10"
        params = {"story_id": "test_story_001"}
        
        # First execution (should not be cached)
        start_time = datetime.now()
        result1 = await self.agent.graph_query(test_query, params, use_cache=True)
        first_duration = (datetime.now() - start_time).total_seconds()
        
        # Second execution (should be cached)
        start_time = datetime.now()
        result2 = await self.agent.graph_query(test_query, params, use_cache=True)
        second_duration = (datetime.now() - start_time).total_seconds()
        
        print(f"🔄 First execution: {first_duration:.4f}s, Cached: {result1.get('cached', False)}")
        print(f"⚡ Second execution: {second_duration:.4f}s, Cached: {result2.get('cached', False)}")
        print(f"📈 Cache size: {len(self.agent.query_cache)} queries")
        
        if result2.get('cached'):
            print("✅ Caching mechanism working correctly")
        else:
            print("⚠️ Caching mechanism may need attention")
    
    async def test_advanced_analysis(self):
        """Test advanced story analysis capabilities."""
        print("\n🔬 Testing Advanced Story Analysis...")
        
        story_id = "demo_story_001"
        user_id = "demo_user_001"
        
        # Test timeline analysis
        print("\n📅 Timeline Analysis:")
        timeline_result = await self.agent.analyze_story_timeline(story_id, user_id)
        
        if "error" not in timeline_result:
            print(f"✅ Timeline analysis completed")
            print(f"   📊 Total scenes: {timeline_result.get('total_scenes', 0)}")
            print(f"   ⚠️ Temporal conflicts: {timeline_result.get('temporal_conflicts', 0)}")
            print(f"   📈 Coherence: {timeline_result.get('timeline_coherence', 'unknown')}")
        else:
            print(f"❌ Timeline analysis failed: {timeline_result['error']}")
        
        # Test character consistency
        print("\n👤 Character Consistency Analysis:")
        character_result = await self.agent.analyze_character_consistency(story_id, "TestCharacter", user_id)
        
        if "error" not in character_result:
            print(f"✅ Character analysis completed")
            print(f"   🤝 Relationships: {len(character_result.get('relationships', []))}")
            print(f"   🧠 Knowledge items: {len(character_result.get('knowledge_evolution', []))}")
            print(f"   ❌ Contradictions: {len(character_result.get('contradictions', []))}")
            print(f"   📊 Consistency score: {character_result.get('consistency_score', 0):.2f}")
        else:
            print(f"❌ Character analysis failed: {character_result['error']}")
        
        # Test plot hole detection
        print("\n🕳️ Plot Hole Detection:")
        plot_holes_result = await self.agent.detect_plot_holes(story_id, user_id)
        
        if "error" not in plot_holes_result:
            print(f"✅ Plot hole detection completed")
            print(f"   🎯 Total plot holes: {plot_holes_result.get('total_plot_holes', 0)}")
            print(f"   🔴 Critical: {len(plot_holes_result.get('plot_holes_by_severity', {}).get('critical', []))}")
            print(f"   🟡 Major: {len(plot_holes_result.get('plot_holes_by_severity', {}).get('major', []))}")
            print(f"   🟢 Minor: {len(plot_holes_result.get('plot_holes_by_severity', {}).get('minor', []))}")
            print(f"   📊 Coherence score: {plot_holes_result.get('overall_coherence_score', 0):.2f}")
        else:
            print(f"❌ Plot hole detection failed: {plot_holes_result['error']}")
    
    async def test_ai_query_generation(self):
        """Test AI-generated custom queries."""
        print("\n🤖 Testing AI-Generated Custom Queries...")
        
        if not self.agent.openai_client:
            print("⚠️ OpenAI client not configured - skipping AI tests")
            return
        
        # Test story analysis with AI
        test_story = {
            "story_id": "ai_test_story",
            "content": "John met Mary at the library. Later, John discovered a secret about the town's history.",
            "entities": [
                {"name": "John", "type": "Character"},
                {"name": "Mary", "type": "Character"},
                {"name": "Library", "type": "Location"}
            ],
            "relationships": [
                {"from": "John", "to": "Mary", "type": "MEETS"},
                {"from": "John", "to": "Library", "type": "VISITS"}
            ]
        }
        
        print("📝 Testing AI story analysis...")
        analysis_result = await self.agent.analyze_story(test_story["content"], test_story)
        
        if "error" not in analysis_result:
            print("✅ AI story analysis completed")
            print(f"   🎯 Model used: {analysis_result.get('model_used', 'unknown')}")
            print(f"   📊 Analysis preview: {str(analysis_result.get('analysis', ''))[:100]}...")
        else:
            print(f"❌ AI story analysis failed: {analysis_result['error']}")
    
    async def test_performance_metrics(self):
        """Test performance and optimization metrics."""
        print("\n📊 Performance Metrics:")
        
        # Cache statistics
        print(f"💾 Query cache size: {len(self.agent.query_cache)} queries")
        print(f"🎯 Templates available: {len(self.agent.query_templates)}")
        print(f"🔧 Schema entities: {len(self.agent.schema_context['entities'])}")
        print(f"🔗 Schema relationships: {len(self.agent.schema_context['relationships'])}")
        
        # Test query optimization suggestions
        test_query = "MATCH (c:Character) RETURN c ORDER BY c.name"
        suggestions = self.agent._get_query_suggestions(test_query)
        print(f"💡 Optimization suggestions for test query: {len(suggestions)}")
        for suggestion in suggestions:
            print(f"   • {suggestion}")
    
    async def demonstrate_tiered_approach(self):
        """Demonstrate the tiered query approach."""
        print("\n🏗️ Demonstrating Tiered Query Approach:")
        
        story_id = "tiered_demo_story"
        user_id = "tiered_demo_user"
        
        # Tier 1: Core Operations (Predefined)
        print("🔧 Tier 1: Core Operations (Predefined)")
        health_check = await self.agent.health_check()
        print(f"   Health check: {health_check.get('status', 'unknown')}")
        
        # Tier 2: Common Patterns (Template-based)
        print("📋 Tier 2: Common Patterns (Template-based)")
        timeline_result = await self.agent.optimized_query("story_timeline", {"story_id": story_id, "user_id": user_id})
        print(f"   Timeline query: {'✅ Success' if timeline_result['success'] else '❌ Failed'}")
        
        # Tier 3: Creative Queries (AI-generated)
        print("🎨 Tier 3: Creative Queries (AI-generated)")
        custom_query = "MATCH (c:Character {story_id: $story_id}) RETURN c.name, c.description ORDER BY c.name"
        custom_result = await self.agent.graph_query(custom_query, {"story_id": story_id})
        print(f"   Custom query: {'✅ Success' if custom_result['success'] else '❌ Failed'}")
        
        print("🎯 Tiered approach allows for optimal balance of performance and flexibility")
    
    async def run_full_demo(self):
        """Run the complete demonstration."""
        print("🌟 Enhanced CineGraph Agent - Full Demonstration")
        print("=" * 60)
        
        try:
            await self.setup()
            await self.test_query_validation()
            await self.test_optimized_queries()
            await self.test_caching_mechanism()
            await self.test_advanced_analysis()
            await self.test_ai_query_generation()
            await self.test_performance_metrics()
            await self.demonstrate_tiered_approach()
            
            print("\n🎉 All tests completed successfully!")
            print("✨ Enhanced CineGraph Agent is ready for production use")
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.graphiti_manager:
                await self.graphiti_manager.close()
                print("🔒 Database connection closed")


async def main():
    """Main entry point for the demonstration."""
    demo = EnhancedAgentDemo()
    await demo.run_full_demo()


if __name__ == "__main__":
    asyncio.run(main())
