#!/usr/bin/env python3
"""
Enhanced CineGraph Agent Setup Script
====================================

This script helps configure and validate the enhanced CineGraph Agent setup.
"""

import os
import sys
import asyncio
from typing import Dict, Any, Optional

def check_environment_variables() -> Dict[str, str]:
    """Check and validate required environment variables."""
    required_vars = {
        'GRAPHITI_DATABASE_URL': 'Database connection URL',
        'GRAPHITI_DATABASE_USER': 'Database username',
        'GRAPHITI_DATABASE_PASSWORD': 'Database password',
        'GRAPHITI_DATABASE_NAME': 'Database name',
        'OPENAI_API_KEY': 'OpenAI API key (optional)',
        'SUPABASE_URL': 'Supabase URL (optional)',
        'SUPABASE_SERVICE_ROLE_KEY': 'Supabase service role key (optional)'
    }
    
    missing_vars = []
    optional_vars = []
    
    print("🔍 Checking environment variables...")
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'password' in var.lower() or 'key' in var.lower():
                displayed_value = f"{'*' * 8}{value[-4:] if len(value) > 4 else '***'}"
            else:
                displayed_value = value
            print(f"  ✅ {var}: {displayed_value}")
        else:
            if var in ['OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']:
                optional_vars.append(var)
                print(f"  ⚠️  {var}: Not set (optional - {description})")
            else:
                missing_vars.append(var)
                print(f"  ❌ {var}: Missing ({description})")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables before running the enhanced agent.")
        return False
    
    if optional_vars:
        print(f"\n⚠️  Optional variables not set: {', '.join(optional_vars)}")
        print("Some features may be limited without these variables.")
    
    print("\n✅ Environment validation passed!")
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    print("📦 Checking dependencies...")
    
    required_packages = [
        'openai',
        'supabase',
        'graphiti-core',
        'asyncio',
        'hashlib',
        'redis'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}: Not installed")
    
    if missing_packages:
        print(f"\n❌ Missing required packages: {', '.join(missing_packages)}")
        print("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    print("\n✅ All dependencies are available!")
    return True

async def test_database_connection():
    """Test database connection."""
    print("🔗 Testing database connection...")
    
    try:
        from core.graphiti_manager import GraphitiManager
        from core.models import GraphitiConfig
        
        config = GraphitiConfig(
            database_url=os.getenv("GRAPHITI_DATABASE_URL", "bolt://localhost:7687"),
            username=os.getenv("GRAPHITI_DATABASE_USER", "neo4j"),
            password=os.getenv("GRAPHITI_DATABASE_PASSWORD", "password"),
            database_name=os.getenv("GRAPHITI_DATABASE_NAME", "neo4j")
        )
        
        manager = GraphitiManager(config)
        await manager.connect()
        
        # Test basic query
        health_check = await manager.health_check()
        
        if health_check.get("status") == "healthy":
            print("  ✅ Database connection successful")
            print(f"  📊 Node count: {health_check.get('node_count', 'unknown')}")
            print(f"  🗄️  Database: {health_check.get('database_name', 'unknown')}")
        else:
            print(f"  ❌ Database unhealthy: {health_check.get('error', 'Unknown error')}")
            return False
        
        await manager.close()
        
    except Exception as e:
        print(f"  ❌ Database connection failed: {str(e)}")
        return False
    
    print("\n✅ Database connection test passed!")
    return True

async def test_enhanced_agent():
    """Test enhanced agent initialization."""
    print("🤖 Testing enhanced agent initialization...")
    
    try:
        from agents.cinegraph_agent import CineGraphAgent
        from core.graphiti_manager import GraphitiManager
        from core.models import GraphitiConfig
        
        # Initialize GraphitiManager
        config = GraphitiConfig(
            database_url=os.getenv("GRAPHITI_DATABASE_URL", "bolt://localhost:7687"),
            username=os.getenv("GRAPHITI_DATABASE_USER", "neo4j"),
            password=os.getenv("GRAPHITI_DATABASE_PASSWORD", "password"),
            database_name=os.getenv("GRAPHITI_DATABASE_NAME", "neo4j")
        )
        
        manager = GraphitiManager(config)
        await manager.connect()
        
        # Initialize Enhanced Agent
        agent = CineGraphAgent(
            graphiti_manager=manager,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
        
        print("  ✅ Enhanced agent initialized successfully")
        print(f"  🎯 Query templates: {len(agent.query_templates)}")
        print(f"  🔧 Schema entities: {len(agent.schema_context['entities'])}")
        print(f"  🔗 Schema relationships: {len(agent.schema_context['relationships'])}")
        
        # Test query validation
        test_query = "MATCH (c:Character {story_id: $story_id}) RETURN c.name"
        validation_result = await agent.validate_query(test_query)
        
        if validation_result["valid"]:
            print("  ✅ Query validation working")
        else:
            print(f"  ❌ Query validation failed: {validation_result['message']}")
            return False
        
        # Test template system
        templates = list(agent.query_templates.keys())
        print(f"  📋 Available templates: {', '.join(templates[:3])}...")
        
        # Test health check
        health_check = await agent.health_check()
        print(f"  💚 Agent health: {health_check.get('status', 'unknown')}")
        
        await manager.close()
        
    except Exception as e:
        print(f"  ❌ Enhanced agent initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ Enhanced agent test passed!")
    return True

def print_usage_examples():
    """Print usage examples for the enhanced agent."""
    print("\n📖 Usage Examples:")
    print("=" * 50)
    
    examples = [
        {
            "title": "Basic Query Validation",
            "code": '''from agents.cinegraph_agent import CineGraphAgent

# Validate a query
result = await agent.validate_query(
    "MATCH (c:Character {story_id: $story_id}) RETURN c.name"
)
print(f"Valid: {result['valid']}")'''
        },
        {
            "title": "Using Query Templates",
            "code": '''# Use optimized template
result = await agent.optimized_query(
    "character_relationships",
    {"story_id": "story_123", "character_name": "John", "user_id": "user_456"}
)'''
        },
        {
            "title": "Advanced Analysis",
            "code": '''# Timeline analysis
timeline = await agent.analyze_story_timeline("story_123", "user_456")

# Character consistency
character_analysis = await agent.analyze_character_consistency(
    "story_123", "John", "user_456"
)

# Plot hole detection
plot_holes = await agent.detect_plot_holes("story_123", "user_456")'''
        },
        {
            "title": "AI-Generated Queries",
            "code": '''# Natural language query
question = "What did John know at the beginning of chapter 3?"
result = await agent.query_story("story_123", question, "user_456")'''
        }
    ]
    
    for example in examples:
        print(f"\n🔸 {example['title']}:")
        print(f"```python\n{example['code']}\n```")

def print_next_steps():
    """Print next steps for using the enhanced agent."""
    print("\n🚀 Next Steps:")
    print("=" * 50)
    print("1. Run the comprehensive demo: python test_enhanced_agent.py")
    print("2. Explore the documentation: docs/enhanced_agent_capabilities.md")
    print("3. Test your own queries with the validation system")
    print("4. Use query templates for common operations")
    print("5. Leverage advanced analysis features for story insights")
    print("6. Monitor performance with caching metrics")
    print("7. Integrate with your existing application")

async def main():
    """Main setup and validation function."""
    print("🌟 Enhanced CineGraph Agent Setup")
    print("=" * 50)
    
    # Check environment variables
    if not check_environment_variables():
        print("\n❌ Setup failed: Missing required environment variables")
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Setup failed: Missing required dependencies")
        sys.exit(1)
    
    # Test database connection
    if not await test_database_connection():
        print("\n❌ Setup failed: Database connection issues")
        sys.exit(1)
    
    # Test enhanced agent
    if not await test_enhanced_agent():
        print("\n❌ Setup failed: Enhanced agent initialization issues")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("✨ Enhanced CineGraph Agent is ready to use!")
    
    # Print usage examples
    print_usage_examples()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    asyncio.run(main())
