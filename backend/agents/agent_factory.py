"""
Agent Factory
=============

Factory functions for creating CineGraphAgent instances with proper dependency injection.
"""

import os
from typing import Optional
from dotenv import load_dotenv

from .cinegraph_agent import CineGraphAgent
from core.graphiti_manager import GraphitiManager
from core.models import GraphitiConfig

load_dotenv()


def create_cinegraph_agent(
    graphiti_manager: Optional[GraphitiManager] = None,
    openai_api_key: Optional[str] = None,
    supabase_url: Optional[str] = None,
    supabase_service_role_key: Optional[str] = None
) -> CineGraphAgent:
    """
    Create a CineGraphAgent instance with proper dependencies.
    
    Args:
        graphiti_manager: Optional GraphitiManager instance. If None, creates a new one.
        openai_api_key: Optional OpenAI API key. If None, loads from environment.
        supabase_url: Optional Supabase URL. If None, loads from environment.
        supabase_service_role_key: Optional Supabase service role key. If None, loads from environment.
        
    Returns:
        Configured CineGraphAgent instance
        
    Raises:
        ValueError: If required environment variables are missing
    """
    # Load configuration from environment if not provided
    openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    supabase_url = supabase_url or os.getenv("SUPABASE_URL")
    supabase_service_role_key = supabase_service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # Validate required configuration
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")
    if not supabase_url:
        raise ValueError("SUPABASE_URL is required")
    if not supabase_service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required")
    
    # Create GraphitiManager if not provided
    if graphiti_manager is None:
        # Support both Aura and local Neo4j
        neo4j_uri = os.getenv("NEO4J_URI", os.getenv("GRAPHITI_DATABASE_URL", "bolt://localhost:7687"))
        neo4j_username = os.getenv("NEO4J_USERNAME", os.getenv("GRAPHITI_DATABASE_USER", "neo4j"))
        neo4j_password = os.getenv("NEO4J_PASSWORD", os.getenv("GRAPHITI_DATABASE_PASSWORD", ""))
        neo4j_database = os.getenv("NEO4J_DATABASE", os.getenv("GRAPHITI_DATABASE_NAME", "neo4j"))
        
        graphiti_config = GraphitiConfig(
            database_url=neo4j_uri,
            username=neo4j_username,
            password=neo4j_password,
            database_name=neo4j_database,
            max_connections=int(os.getenv("GRAPHITI_MAX_CONNECTIONS", "10")),
            connection_timeout=int(os.getenv("GRAPHITI_CONNECTION_TIMEOUT", "30"))
        )
        graphiti_manager = GraphitiManager(graphiti_config)
    
    # Create and return CineGraphAgent
    agent = CineGraphAgent(
        graphiti_manager=graphiti_manager,
        openai_api_key=openai_api_key,
        supabase_url=supabase_url,
        supabase_key=supabase_service_role_key
    )
    
    return agent


async def initialize_cinegraph_agent(agent: CineGraphAgent) -> CineGraphAgent:
    """
    Initialize a CineGraphAgent instance with proper setup.
    
    Args:
        agent: CineGraphAgent instance to initialize
        
    Returns:
        Initialized CineGraphAgent instance
    """
    # Initialize GraphitiManager connection
    await agent.graphiti_manager.initialize()
    
    # Initialize the agent itself (starts Redis listener)
    await agent.initialize()
    
    return agent


# Global agent instance (optional, for singleton pattern)
_global_agent: Optional[CineGraphAgent] = None


async def get_global_agent() -> CineGraphAgent:
    """
    Get or create the global CineGraphAgent instance.
    
    Returns:
        Global CineGraphAgent instance
    """
    global _global_agent
    
    if _global_agent is None:
        _global_agent = create_cinegraph_agent()
        await initialize_cinegraph_agent(_global_agent)
    
    return _global_agent


def reset_global_agent():
    """Reset the global agent instance (useful for testing)."""
    global _global_agent
    _global_agent = None
