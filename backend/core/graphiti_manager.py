"""
GraphitiManager - Async Wrapper for Graphiti Core
=================================================

This module provides an async wrapper around the graphiti-core client with
specialized methods for story management, temporal queries, and knowledge graph operations.
"""

import os
import asyncio
import uuid
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.edges import EntityEdge

from .models import (
    StoryGraph, CharacterKnowledge, GraphEntity, GraphRelationship,
    EntityType, RelationshipType, GraphitiConfig, TemporalQuery
)


class GraphitiManager:
    """
    Async wrapper for Graphiti Core client with story-specific functionality.
    
    Provides high-level methods for story management, temporal queries,
    and knowledge graph operations with proper error handling and connection management.
    """
    
    def __init__(self, config: Optional[GraphitiConfig] = None):
        """
        Initialize GraphitiManager with configuration.
        
        Args:
            config: Optional GraphitiConfig object. If None, will load from environment.
        """
        self.config = config or self._load_config_from_env()
        self.client: Optional[Graphiti] = None
        self._connection_pool_size = self.config.max_connections
        self._connection_timeout = self.config.connection_timeout
        self._session_id: Optional[str] = None
        self._story_sessions: Dict[str, str] = {}  # story_id -> session_id mapping
    
        
    def _load_config_from_env(self) -> GraphitiConfig:
        """Load configuration from environment variables."""
        # Support both Aura and local Neo4j
        neo4j_uri = os.getenv("NEO4J_URI", os.getenv("GRAPHITI_DATABASE_URL", "bolt://localhost:7687"))
        neo4j_username = os.getenv("NEO4J_USERNAME", os.getenv("GRAPHITI_DATABASE_USER", "neo4j"))
        neo4j_password = os.getenv("NEO4J_PASSWORD", os.getenv("GRAPHITI_DATABASE_PASSWORD", ""))
        neo4j_database = os.getenv("NEO4J_DATABASE", os.getenv("GRAPHITI_DATABASE_NAME", "neo4j"))
        
        return GraphitiConfig(
            database_url=neo4j_uri,
            username=neo4j_username,
            password=neo4j_password,
            database_name=neo4j_database,
            max_connections=int(os.getenv("GRAPHITI_MAX_CONNECTIONS", "10")),
            connection_timeout=int(os.getenv("GRAPHITI_CONNECTION_TIMEOUT", "30"))
        )
    
    async def connect(self) -> None:
        """
        Initialize connection to Graphiti database.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.client = Graphiti(
                uri=self.config.database_url,
                user=self.config.username,
                password=self.config.password
            )
            
            # Test connection
            await self.client.build_indices_and_constraints()
            print(f"Connected to Graphiti database at {self.config.database_url}")
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Graphiti database: {str(e)}")
    
    async def initialize(self) -> None:
        """Initialize the GraphitiManager and establish connection."""
        await self.connect()
    
    async def close(self) -> None:
        """Close the connection to Graphiti database."""
        if self.client:
            # Check if client has close method
            if hasattr(self.client, 'close') and callable(self.client.close):
                try:
                    # close() is synchronous in Graphiti 0.3.0
                    await asyncio.to_thread(self.client.close)
                except Exception as e:
                    print(f"Warning: Error closing client connection: {e}")
            self.client = None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the Graphiti connection using episodic APIs.
        
        Returns:
            Dict containing health status and connection info
        """
        try:
            if not self.client:
                return {"status": "disconnected", "error": "No client connection"}
            
            # Test connection using episodic API - search with minimal query
            try:
                # Use search API to confirm connectivity instead of counting nodes
                search_result = await self.client.search(
                    query='*', 
                    group_ids=None, 
                    num_results=1
                )
                connectivity_confirmed = search_result is not None
                search_result_count = len(search_result) if search_result else 0
            except Exception as query_error:
                # Log the query error but don't fail the health check
                print(f"Health check search error: {query_error}")
                connectivity_confirmed = False
                search_result_count = "unknown"
            
            return {
                "status": "healthy" if connectivity_confirmed else "degraded",
                "database_url": self.config.database_url,
                "database_name": self.config.database_name,
                "connectivity_confirmed": connectivity_confirmed,
                "search_result_count": search_result_count,
                "connection_timeout": self.config.connection_timeout,
                "note": "Health check using episodic API (search)"
            }
            
        except Exception as e:
            # Never raise exceptions from health_check - always return status
            print(f"Health check error: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "database_url": self.config.database_url if hasattr(self, 'config') else "unknown"
            }
    
    async def add_story_content(self, content: str, extracted_data: Dict[str, Any], 
                               story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Add story content to the knowledge graph using episodic memory.
        
        Args:
            content: Raw story content
            extracted_data: Processed story data with entities and relationships
            story_id: Unique story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing operation results
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Extract entities and relationships from the processed data
            entities = extracted_data.get("entities", [])
            relationships = extracted_data.get("relationships", [])
            
            # Get or create session for this story
            session_id = self._story_sessions.get(story_id)
            if not session_id:
                session_id = await self.create_story_session(story_id)
            
            # Add the content as an episode instead of using add_node
            episode_content = f"Story Content: {content}\n\nEntities: {entities}\n\nRelationships: {relationships}"
            
            episode_result = await self.client.add_episode(
                name=f"Story Content - {story_id}",
                episode_body=episode_content,
                source_description=f"Story content for {story_id} by user {user_id}",
                reference_time=datetime.utcnow(),
                group_id=session_id
            )
            
            # Get episode ID with defensive attribute checking
            episode_id = None
            if episode_result:
                for attr_name in ['uuid', 'id', 'episode_id']:
                    if hasattr(episode_result, attr_name):
                        episode_id = getattr(episode_result, attr_name)
                        break
            
            return {
                "status": "success",
                "story_id": story_id,
                "entities_added": len(entities),
                "relationships_added": len(relationships),
                "episode_id": episode_id,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Content added as episodic memory (Graphiti 0.3.0 compatible)"
            }
            
        except Exception as e:
            logging.error(f"Error adding story content: {e}")
            return {
                "status": "error",
                "error": str(e),
                "story_id": story_id
            }
    
    async def get_story_graph(self, story_id: str, user_id: str) -> StoryGraph:
        """
        Retrieve the complete knowledge graph for a story using episodic memory.
        
        Args:
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            StoryGraph object containing entities and relationships
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Get session for this story
            session_id = self._story_sessions.get(story_id)
            if not session_id:
                return StoryGraph(
                    story_id=story_id,
                    entities=[],
                    relationships=[],
                    metadata={"entity_count": 0, "relationship_count": 0, "note": "No session found for story"},
                    last_updated=datetime.utcnow()
                )
            
            # Use search to find story-related episodes
            search_results = await self.client.search(
                query=f"story {story_id}",
                group_ids=[session_id],
                num_results=50
            )
            
            # Extract entities and relationships from episodes
            entities = []
            relationships = []
            
            for result in search_results:
                # Parse episode content for entities and relationships
                # This is a simplified approach since we're working with episodic memory
                if hasattr(result, 'episode_body'):
                    content = result.episode_body
                    # Simple entity extraction (would need more sophisticated parsing in real use)
                    if "Entities:" in content:
                        entities_section = content.split("Entities:")[1].split("\n\nRelationships:")[0]
                        # Add basic entity parsing logic here
                        pass
            
            return StoryGraph(
                story_id=story_id,
                entities=entities,
                relationships=relationships,
                metadata={
                    "entity_count": len(entities), 
                    "relationship_count": len(relationships),
                    "episodes_found": len(search_results),
                    "note": "Generated from episodic memory (Graphiti 0.3.0 compatible)"
                },
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logging.error(f"Failed to retrieve story graph: {e}")
            raise RuntimeError(f"Failed to retrieve story graph: {str(e)}")
    
    async def get_character_knowledge(self, story_id: str, character_name: str, 
                                    timestamp: Optional[str] = None, user_id: Optional[str] = None) -> CharacterKnowledge:
        """
        Get what a character knows at a specific point in time using episodic memory.
        
        Args:
            story_id: Story identifier
            character_name: Character name
            timestamp: Optional timestamp for temporal queries
            user_id: User ID for data isolation
            
        Returns:
            CharacterKnowledge object
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Get session for this story
            session_id = self._story_sessions.get(story_id)
            if not session_id:
                return CharacterKnowledge(
                    character_id=character_name,
                    character_name=character_name,
                    knowledge_items=[],
                    timestamp=datetime.fromisoformat(timestamp) if timestamp else None,
                    story_id=story_id
                )
            
            # Search for episodes related to this character
            search_results = await self.client.search(
                query=f"character {character_name} story {story_id}",
                group_ids=[session_id],
                num_results=20
            )
            
            # Extract knowledge items from episodes
            knowledge_items = []
            for result in search_results:
                if hasattr(result, 'episode_body'):
                    knowledge_items.append({
                        "content": result.episode_body,
                        "timestamp": getattr(result, 'created_at', datetime.utcnow().isoformat()),
                        "type": "episodic_memory"
                    })
            
            return CharacterKnowledge(
                character_id=character_name,
                character_name=character_name,
                knowledge_items=knowledge_items,
                timestamp=datetime.fromisoformat(timestamp) if timestamp else None,
                story_id=story_id
            )
            
        except Exception as e:
            logging.error(f"Failed to retrieve character knowledge: {e}")
            raise RuntimeError(f"Failed to retrieve character knowledge: {str(e)}")
    
    async def delete_story(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete a story and all its associated data from episodic memory.
        
        Args:
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing deletion results
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Remove story session tracking
            session_id = self._story_sessions.pop(story_id, None)
            
            # Note: Graphiti 0.3.0 doesn't provide direct episode deletion
            # In a full implementation, you might need to track episodes and delete them
            # For now, we'll just remove the session mapping
            
            return {
                "status": "success",
                "story_id": story_id,
                "deleted_at": datetime.utcnow().isoformat(),
                "message": f"Story {story_id} session removed from tracking",
                "note": "Episodes remain in Graphiti but are no longer tracked by this session"
            }
            
        except Exception as e:
            logging.error(f"Error deleting story: {e}")
            return {
                "status": "error",
                "error": str(e),
                "story_id": story_id
            }
    
    # Helper methods for entity and relationship management
    
    async def upsert_entity(self, entity_type: str, properties: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create or update an entity in the knowledge graph using episodic memory.
        
        Args:
            entity_type: Type of entity (Character, Location, etc.)
            properties: Entity properties
            user_id: User ID for data isolation (optional, can be in properties)
            
        Returns:
            Dict containing operation results
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Ensure user_id is included in properties
            final_properties = {**properties}
            if user_id and "user_id" not in final_properties:
                final_properties["user_id"] = user_id
            
            # Create entity as episodic memory instead of graph node
            entity_description = f"Entity: {entity_type}\nName: {properties.get('name', 'Unknown')}\nProperties: {final_properties}"
            
            # Get a general session for entities (could be story-specific)
            story_id = final_properties.get("story_id", "general")
            session_id = self._story_sessions.get(story_id)
            if not session_id:
                session_id = await self.create_story_session(story_id)
            
            episode_result = await self.client.add_episode(
                name=f"Entity: {entity_type} - {properties.get('name', 'Unknown')}",
                episode_body=entity_description,
                source_description=f"Entity creation for {entity_type}",
                reference_time=datetime.utcnow(),
                group_id=session_id
            )
            
            # Get episode ID with defensive attribute checking
            episode_id = None
            if episode_result:
                for attr_name in ['uuid', 'id', 'episode_id']:
                    if hasattr(episode_result, attr_name):
                        episode_id = getattr(episode_result, attr_name)
                        break
            
            return {
                "status": "success",
                "entity_type": entity_type,
                "entity_id": properties.get("id", properties.get("name")),
                "episode_id": episode_id,
                "operation": "upserted",
                "note": "Entity stored as episodic memory (Graphiti 0.3.0 compatible)"
            }
            
        except Exception as e:
            logging.error(f"Error upserting entity: {e}")
            return {
                "status": "error",
                "error": str(e),
                "entity_type": entity_type
            }
    
    async def upsert_relationship(self, relationship_type: str, from_id: str, to_id: str, 
                                 properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a relationship in the knowledge graph using episodic memory.
        
        Args:
            relationship_type: Type of relationship
            from_id: Source entity ID
            to_id: Target entity ID
            properties: Relationship properties
            
        Returns:
            Dict containing operation results
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Create relationship as episodic memory instead of graph edge
            relationship_description = f"Relationship: {relationship_type}\nFrom: {from_id}\nTo: {to_id}\nProperties: {properties}"
            
            # Get a general session for relationships
            story_id = properties.get("story_id", "general")
            session_id = self._story_sessions.get(story_id)
            if not session_id:
                session_id = await self.create_story_session(story_id)
            
            episode_result = await self.client.add_episode(
                name=f"Relationship: {from_id} -{relationship_type}-> {to_id}",
                episode_body=relationship_description,
                source_description=f"Relationship creation: {relationship_type}",
                reference_time=datetime.utcnow(),
                group_id=session_id
            )
            
            # Get episode ID with defensive attribute checking
            episode_id = None
            if episode_result:
                for attr_name in ['uuid', 'id', 'episode_id']:
                    if hasattr(episode_result, attr_name):
                        episode_id = getattr(episode_result, attr_name)
                        break
            
            return {
                "status": "success",
                "relationship_type": relationship_type,
                "from_id": from_id,
                "to_id": to_id,
                "episode_id": episode_id,
                "operation": "upserted",
                "note": "Relationship stored as episodic memory (Graphiti 0.3.0 compatible)"
            }
            
        except Exception as e:
            logging.error(f"Error upserting relationship: {e}")
            return {
                "status": "error",
                "error": str(e),
                "relationship_type": relationship_type,
                "from_id": from_id,
                "to_id": to_id
            }
    
    async def execute_temporal_query(self, query: TemporalQuery) -> List[Dict[str, Any]]:
        """
        Execute a temporal query using episodic memory search and retrieve_episodes APIs.
        No direct Cypher queries are used.
        
        Args:
            query: TemporalQuery object containing query parameters
            
        Returns:
            List of query results formatted for temporal analysis
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Use episodic memory retrieval with temporal constraints
            story_id = query.entity_filters.get("story_id") if query.entity_filters else "general"
            session_id = self._story_sessions.get(story_id)
            
            if not session_id:
                # If no session found, try searching across all sessions
                all_sessions = list(self._story_sessions.values())
                if not all_sessions:
                    return []
                session_ids = all_sessions
            else:
                session_ids = [session_id]
            
            # Retrieve episodes around the reference time using episodic API
            episodes = await self.client.retrieve_episodes(
                reference_time=query.timestamp,
                last_n=20,  # Get more episodes for better temporal context
                group_ids=session_ids
            )
            
            # Also use search API to find related content
            search_query = query.entity_filters.get("search_term", "*") if query.entity_filters else "*"
            search_results = await self.client.search(
                query=search_query,
                group_ids=session_ids,
                num_results=10
            )
            
            # Filter and format episodes as temporal results
            results = []
            
            # Process retrieved episodes
            for episode in episodes:
                if hasattr(episode, 'created_at'):
                    episode_time = episode.created_at
                    if episode_time <= query.timestamp:
                        results.append({
                            "source": {"name": "episode", "type": "temporal_episode"},
                            "relationship": {
                                "type": "TEMPORAL_REFERENCE", 
                                "created_at": episode_time.isoformat(),
                                "source_api": "retrieve_episodes"
                            },
                            "target": {
                                "content": getattr(episode, 'episode_body', ''), 
                                "uuid": getattr(episode, 'uuid', ''),
                                "group_id": getattr(episode, 'group_id', '')
                            }
                        })
            
            # Process search results for additional temporal context
            for result in search_results:
                if hasattr(result, 'created_at'):
                    result_time = result.created_at
                    if result_time <= query.timestamp:
                        results.append({
                            "source": {"name": "search_result", "type": "temporal_search"},
                            "relationship": {
                                "type": "SEARCH_MATCH", 
                                "created_at": result_time.isoformat(),
                                "source_api": "search"
                            },
                            "target": {
                                "content": getattr(result, 'episode_body', getattr(result, 'fact', '')), 
                                "uuid": getattr(result, 'uuid', ''),
                                "group_id": getattr(result, 'group_id', '')
                            }
                        })
            
            # Sort results by timestamp
            results.sort(key=lambda x: x["relationship"]["created_at"])
            
            return results
            
        except Exception as e:
            logging.error(f"Failed to execute temporal query using episodic APIs: {e}")
            raise RuntimeError(f"Failed to execute temporal query: {str(e)}")
    
    async def get_query_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph using episodic memory APIs.
        Derives counts from _story_sessions and search result lengths.
        
        Returns:
            Dict containing graph statistics
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Get statistics from session tracking
            total_sessions = len(self._story_sessions)
            story_count = len(set(self._story_sessions.keys()))
            
            # Get episode counts across all sessions using search API
            total_episodes = 0
            episode_breakdown = {}
            
            for story_id, session_id in self._story_sessions.items():
                try:
                    # Use search API to get episode count for each session
                    search_results = await self.client.search(
                        query="*",
                        group_ids=[session_id],
                        num_results=1000  # Get more results for better count
                    )
                    episode_count = len(search_results) if search_results else 0
                    episode_breakdown[story_id] = episode_count
                    total_episodes += episode_count
                except Exception:
                    episode_breakdown[story_id] = "unknown"
            
            # Try to get additional statistics using retrieve_episodes
            recent_episode_count = 0
            try:
                # Get recent episodes across all sessions
                all_sessions = list(self._story_sessions.values())
                if all_sessions:
                    recent_episodes = await self.client.retrieve_episodes(
                        reference_time=datetime.utcnow(),
                        last_n=50,
                        group_ids=all_sessions[:5]  # Limit to first 5 sessions to avoid timeout
                    )
                    recent_episode_count = len(recent_episodes) if recent_episodes else 0
            except Exception:
                recent_episode_count = "unknown"
            
            return {
                "session_count": total_sessions,
                "story_count": story_count,
                "total_episodes": total_episodes,
                "recent_episodes": recent_episode_count,
                "episode_breakdown_by_story": episode_breakdown,
                "active_sessions": list(self._story_sessions.keys()),
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Statistics from episodic memory using search and retrieve_episodes APIs (Graphiti 0.3.0 compatible)",
                "api_methods_used": ["search", "retrieve_episodes"]
            }
            
        except Exception as e:
            logging.error(f"Error getting statistics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Error occurred while gathering statistics via episodic APIs"
            }
    
    # === ZEP-LIKE MEMORY MANAGEMENT METHODS ===
    
    async def create_story_session(self, story_id: str, session_id: Optional[str] = None) -> str:
        """
        Create a new story session for episodic memory management.
        
        Args:
            story_id: Story identifier
            session_id: Optional session ID. If not provided, generates a new one.
            
        Returns:
            Session ID for the created session
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        session_id = session_id or f"session_{story_id}_{uuid.uuid4().hex[:8]}"
        
        # Initialize session in Graphiti - this would typically create episodic context
        episode_result = await self.client.add_episode(
            name=f"Story Session: {story_id}",
            episode_body=f"Starting new story session for {story_id}",
            source_description=f"Story session initialization for {story_id}",
            reference_time=datetime.utcnow(),
            group_id=session_id
        )
        
        # Capture the returned session_id from the episode for future calls
        if episode_result and hasattr(episode_result, 'group_id') and episode_result.group_id:
            session_id = episode_result.group_id
        
        self._story_sessions[story_id] = session_id
        
        return session_id
    
    async def add_memory(self, story_id: str, content: str, role: str = "user", 
                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add a memory episode to the story session (Zep-like add_message functionality).
        
        Args:
            story_id: Story identifier
            content: Memory content to add
            role: Role of the memory (user, assistant, system)
            metadata: Optional metadata for the memory
            
        Returns:
            Dict containing operation results
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        # Get or create session for this story
        session_id = self._story_sessions.get(story_id)
        if not session_id:
            session_id = await self.create_story_session(story_id)
        
        try:
            # Use Graphiti's episodic memory capabilities
            episode_result = await self.client.add_episode(
                name=f"{role.title()} Memory - {story_id}",
                episode_body=content,
                source_description=f"{role} input for story {story_id}",
                reference_time=datetime.utcnow(),
                group_id=session_id
            )
            
            # Capture the returned session_id from the episode for future calls
            if episode_result and hasattr(episode_result, 'group_id') and episode_result.group_id:
                session_id = episode_result.group_id
                self._story_sessions[story_id] = session_id
            
            # Get episode ID with defensive attribute checking
            episode_id = None
            if episode_result:
                for attr_name in ['uuid', 'id', 'episode_id']:
                    if hasattr(episode_result, attr_name):
                        episode_id = getattr(episode_result, attr_name)
                        break
            
            return {
                "status": "success",
                "story_id": story_id,
                "session_id": session_id,
                "episode_id": episode_id,
                "role": role,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "story_id": story_id
            }
    
    async def get_memory(self, story_id: str, limit: int = 10) -> str:
        """
        Get memory context for a story (Zep-like get_memory functionality).
        
        Args:
            story_id: Story identifier
            limit: Maximum number of recent memories to include
            
        Returns:
            Formatted memory context string
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        session_id = self._story_sessions.get(story_id)
        if not session_id:
            return "No memory context available for this story."
        
        try:
            # Search for recent episodes in this session using new API
            search_results = await self.client.search(
                query=f"story session {story_id}",
                group_ids=[session_id],
                num_results=limit
            )
            
            # Format the results into memory context
            memory_parts = []
            for result in search_results:
                if hasattr(result, 'episode_body'):
                    memory_parts.append(result.episode_body)
                elif hasattr(result, 'content'):
                    memory_parts.append(result.content)
            
            if memory_parts:
                return "\n\n".join(memory_parts)
            else:
                return "No recent memory context found."
                
        except Exception as e:
            return f"Error retrieving memory context: {str(e)}"
    
    async def search_memory(self, story_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search story memory for relevant context (Zep-like search_memory functionality).
        
        Args:
            story_id: Story identifier
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant memory items
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        session_id = self._story_sessions.get(story_id)
        if not session_id:
            return []
        
        try:
            # Use Graphiti's episode search with new API
            search_results = await self.client.search(
                query=query,
                group_ids=[session_id],
                num_results=limit
            )
            
            # Format results for return
            formatted_results = []
            for result in search_results:
                formatted_result = {
                    "content": getattr(result, 'episode_body', getattr(result, 'content', '')),
                    "score": getattr(result, 'score', 0.0),
                    "timestamp": getattr(result, 'created_at', datetime.utcnow().isoformat()),
                    "metadata": getattr(result, 'metadata', {})
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching memory: {str(e)}")
            return []
    
    async def get_story_summary(self, story_id: str) -> str:
        """
        Get an AI-generated summary of the story using Graphiti's capabilities.
        
        Args:
            story_id: Story identifier
            
        Returns:
            Story summary string
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Use Graphiti's summarization capabilities
            # Note: get_summary may not exist in 0.3.0 API - handle gracefully
            if hasattr(self.client, 'get_summary'):
                summary_results = await self.client.get_summary(
                    group_id=self._story_sessions.get(story_id),
                    summary_type="story_overview"
                )
            else:
                # Fallback if get_summary doesn't exist
                return "Summary generation not available in current API version."
            
            return summary_results.summary if hasattr(summary_results, 'summary') else "No summary available."
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    async def extract_facts(self, story_id: str, content: str) -> List[Dict[str, Any]]:
        """
        Extract facts from story content using Graphiti 0.3.0 approach.
        In 0.3.0, facts are extracted automatically when adding episodes.
        This method searches for the extracted relationships/entities.
        
        Args:
            story_id: Story identifier
            content: Content to extract facts from
            
        Returns:
            List of extracted facts (actually search results)
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # In Graphiti 0.3.0, extract_facts doesn't exist
            # Instead, we search for entities/relationships that were created
            session_id = self._story_sessions.get(story_id)
            if not session_id:
                return []
            
            # Search for content related to this story
            search_results = await self.client.search(
                query=content[:100],  # Use first 100 chars
                group_ids=[session_id],
                num_results=10
            )
            
            # Convert search results to fact-like format for compatibility
            facts = []
            for result in search_results:
                if hasattr(result, 'fact') and result.fact:
                    facts.append({
                        "fact": result.fact,
                        "entities": [],  # EntityEdge doesn't directly expose entity names
                        "confidence": 0.8,  # Default confidence
                        "timestamp": getattr(result, 'created_at', datetime.utcnow()).isoformat() if hasattr(result, 'created_at') else datetime.utcnow().isoformat(),
                        "type": type(result).__name__,
                        "uuid": getattr(result, 'uuid', None)
                    })
            
            return facts
            
        except Exception as e:
            print(f"Error extracting facts (Graphiti 0.3.0): {str(e)}")
            return []
    
    async def get_temporal_context(self, story_id: str, timestamp: datetime, 
                                  context_window: int = 5) -> Dict[str, Any]:
        """
        Get story context at a specific point in time using Graphiti's bi-temporal model.
        
        Args:
            story_id: Story identifier
            timestamp: Timestamp for temporal query
            context_window: Number of events before/after to include
            
        Returns:
            Dict containing temporal context
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Use Graphiti's bi-temporal capabilities
            temporal_query = TemporalQuery(
                timestamp=timestamp,
                entity_filters={"story_id": story_id},
                relationship_filters={"story_id": story_id}
            )
            
            temporal_results = await self.execute_temporal_query(temporal_query)
            
            # Get events around the timestamp
            events_before = []
            events_after = []
            events_at_time = []
            
            for result in temporal_results:
                event_time = datetime.fromisoformat(result.get("relationship", {}).get("created_at", timestamp.isoformat()))
                
                if event_time < timestamp:
                    events_before.append(result)
                elif event_time > timestamp:
                    events_after.append(result)
                else:
                    events_at_time.append(result)
            
            # Sort and limit results
            events_before = sorted(events_before, key=lambda x: x.get("relationship", {}).get("created_at", ""))[-context_window:]
            events_after = sorted(events_after, key=lambda x: x.get("relationship", {}).get("created_at", ""))[:context_window]
            
            return {
                "timestamp": timestamp.isoformat(),
                "events_before": events_before,
                "events_at_time": events_at_time,
                "events_after": events_after,
                "context_summary": f"Found {len(events_before)} events before, {len(events_at_time)} at time, {len(events_after)} after"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": timestamp.isoformat()
            }
    
    async def get_active_stories(self) -> List[str]:
        """
        Get list of active story IDs from tracked sessions.
        
        Returns:
            List of story IDs that are currently active
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Return all currently tracked story sessions
            active_stories = list(self._story_sessions.keys())
            return active_stories
            
        except Exception as e:
            logging.error(f"Error getting active stories: {e}")
            return []
    
    async def detect_contradictions(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """
        DETECT_CONTRADICTIONS procedure - Built-in Graphiti procedure for detecting contradictions.
        
        Args:
            story_id: Story identifier to scope the detection
            user_id: User ID for data isolation
            
        Returns:
            Dict containing detection results
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Import here to avoid circular import
            from graphiti.rules.consistency_engine import ConsistencyEngine
            
            # Create consistency engine instance
            consistency_engine = ConsistencyEngine(self.client)
            
            # Run contradiction detection
            result = await consistency_engine.detect_contradictions(story_id, user_id)
            
            return {
                "status": "success",
                "story_id": story_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "story_id": story_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _run_cypher_query(self, cypher: str) -> Any:
        """
        Run a direct Cypher query against the graph database.
        
        This is a controlled escape hatch for admin/debug code that provides
        direct access to Cypher queries while discouraging normal use.
        
        Args:
            cypher: The Cypher query string to execute
            
        Returns:
            Query results from the database
            
        Raises:
            RuntimeError: If client not connected or feature flag not enabled
            ValueError: If cypher query is empty or invalid
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        # Check if direct Cypher queries are allowed via environment variable
        if not os.getenv("GRAPHITI_ALLOW_CYPHER", "false").lower() == "true":
            raise RuntimeError(
                "Direct Cypher queries are disabled. Set GRAPHITI_ALLOW_CYPHER=true to enable this feature."
            )
        
        if not cypher or not cypher.strip():
            raise ValueError("Cypher query cannot be empty")
        
        # Log warning about direct Cypher usage
        logging.warning(
            "Direct Cypher query execution detected. This bypasses normal GraphitiManager abstractions. "
            "Query: %s", cypher[:100] + "..." if len(cypher) > 100 else cypher
        )
        
        try:
            # Use get_nodes_by_query for Graphiti ≤0.3 compatibility
            result = await self.client.get_nodes_by_query(cypher)
            
            # Log successful execution
            logging.info(
                "Direct Cypher query executed successfully. Returned %d result(s)", 
                len(result) if result else 0
            )
            
            return result
            
        except Exception as e:
            logging.error("Direct Cypher query failed: %s", str(e))
            raise RuntimeError(f"Cypher query execution failed: {str(e)}")
