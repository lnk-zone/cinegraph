"""
GraphitiManager - Async Wrapper for Graphiti Core
=================================================

This module provides an async wrapper around the graphiti-core client with
specialized methods for story management, temporal queries, and knowledge graph operations.
"""

import os
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search_config import SearchConfig, EpisodeSearchConfig

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
                password=self.config.password,
                database=self.config.database_name
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
            await self.client.close()
            self.client = None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the Graphiti connection.
        
        Returns:
            Dict containing health status and connection info
        """
        try:
            if not self.client:
                return {"status": "disconnected", "error": "No client connection"}
            
            # Simple query to test connection
            query = "MATCH (n) RETURN count(n) as node_count LIMIT 1"
            result = await self.client.query(query)
            
            return {
                "status": "healthy",
                "database_url": self.config.database_url,
                "database_name": self.config.database_name,
                "node_count": result[0]["node_count"] if result else 0,
                "connection_timeout": self.config.connection_timeout
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "database_url": self.config.database_url
            }
    
    async def add_story_content(self, content: str, extracted_data: Dict[str, Any], 
                               story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Add story content to the knowledge graph.
        
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
            
            # Create story node if it doesn't exist
            story_node = EntityNode(
                name=f"Story_{story_id}",
                labels=["Story"],
                properties={
                    "story_id": story_id,
                    "user_id": user_id,
                    "content": content,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            await self.client.add_node(story_node)
            
            # Add entities to the graph
            entity_nodes = []
            for entity in entities:
                entity_node = EntityNode(
                    name=entity.get("name", "Unknown"),
                    labels=[entity.get("type", "Entity")],
                    properties={
                        **entity,
                        "story_id": story_id,
                        "user_id": user_id,
                        "created_at": datetime.utcnow().isoformat()
                    }
                )
                await self.client.add_node(entity_node)
                entity_nodes.append(entity_node)
            
            # Add relationships
            for relationship in relationships:
                await self.upsert_relationship(
                    relationship.get("type", "RELATED_TO"),
                    relationship.get("from_id"),
                    relationship.get("to_id"),
                    {
                        **relationship.get("properties", {}),
                        "story_id": story_id,
                        "user_id": user_id,
                        "created_at": datetime.utcnow().isoformat()
                    }
                )
            
            return {
                "status": "success",
                "story_id": story_id,
                "entities_added": len(entities),
                "relationships_added": len(relationships),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "story_id": story_id
            }
    
    async def get_story_graph(self, story_id: str, user_id: str) -> StoryGraph:
        """
        Retrieve the complete knowledge graph for a story.
        
        Args:
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            StoryGraph object containing entities and relationships
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Query for all entities in the story
            entities_query = """
            MATCH (n)
            WHERE n.story_id = $story_id AND n.user_id = $user_id
            RETURN n
            """
            
            entity_results = await self.client.query(entities_query, {"story_id": story_id, "user_id": user_id})
            entities = []
            
            for result in entity_results:
                node = result["n"]
                entities.append(GraphEntity(
                    id=node.get("id", str(node.identity)),
                    type=EntityType(node.get("type", "CHARACTER")),
                    name=node.get("name", "Unknown"),
                    properties=dict(node),
                    created_at=datetime.fromisoformat(node.get("created_at", datetime.utcnow().isoformat())),
                    updated_at=datetime.fromisoformat(node.get("updated_at")) if node.get("updated_at") else None
                ))
            
            # Query for all relationships in the story
            relationships_query = """
            MATCH (a)-[r]->(b)
            WHERE a.story_id = $story_id AND b.story_id = $story_id 
            AND a.user_id = $user_id AND b.user_id = $user_id
            RETURN r, a, b
            """
            
            relationship_results = await self.client.query(relationships_query, {"story_id": story_id, "user_id": user_id})
            relationships = []
            
            for result in relationship_results:
                rel = result["r"]
                from_node = result["a"]
                to_node = result["b"]
                
                relationships.append(GraphRelationship(
                    type=RelationshipType(rel.type),
                    from_id=from_node.get("id", str(from_node.identity)),
                    to_id=to_node.get("id", str(to_node.identity)),
                    properties=dict(rel),
                    created_at=datetime.fromisoformat(rel.get("created_at", datetime.utcnow().isoformat())),
                    updated_at=datetime.fromisoformat(rel.get("updated_at")) if rel.get("updated_at") else None
                ))
            
            return StoryGraph(
                story_id=story_id,
                entities=entities,
                relationships=relationships,
                metadata={"entity_count": len(entities), "relationship_count": len(relationships)},
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve story graph: {str(e)}")
    
    async def get_character_knowledge(self, story_id: str, character_name: str, 
                                    timestamp: Optional[str] = None, user_id: Optional[str] = None) -> CharacterKnowledge:
        """
        Get what a character knows at a specific point in time.
        
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
            # Build temporal query if timestamp is provided
            temporal_clause = ""
            params = {"story_id": story_id, "character_name": character_name}
            
            if user_id:
                params["user_id"] = user_id
            
            if timestamp:
                temporal_clause = "AND k.valid_from <= $timestamp AND (k.valid_to IS NULL OR k.valid_to >= $timestamp)"
                params["timestamp"] = timestamp
            
            # Query for character's knowledge
            user_filter = "AND c.user_id = $user_id AND k.user_id = $user_id" if user_id else ""
            knowledge_query = f"""
            MATCH (c:Character {{name: $character_name, story_id: $story_id}})-[knows:KNOWS]->(k:Knowledge)
            WHERE k.story_id = $story_id {user_filter} {temporal_clause}
            RETURN k
            ORDER BY k.created_at
            """
            
            knowledge_results = await self.client.query(knowledge_query, params)
            knowledge_items = []
            
            for result in knowledge_results:
                knowledge = result["k"]
                knowledge_items.append(dict(knowledge))
            
            # Get character ID
            character_query = f"""
            MATCH (c:Character {{name: $character_name, story_id: $story_id}})
            WHERE 1=1 {user_filter}
            RETURN c.id as character_id
            """
            
            character_result = await self.client.query(character_query, params)
            character_id = character_result[0]["character_id"] if character_result else character_name
            
            return CharacterKnowledge(
                character_id=character_id,
                character_name=character_name,
                knowledge_items=knowledge_items,
                timestamp=datetime.fromisoformat(timestamp) if timestamp else None,
                story_id=story_id
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve character knowledge: {str(e)}")
    
    async def delete_story(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete a story and all its associated data from the knowledge graph.
        
        Args:
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing deletion results
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Delete all relationships first
            relationships_query = """
            MATCH (a)-[r]->(b)
            WHERE a.story_id = $story_id AND b.story_id = $story_id
            AND a.user_id = $user_id AND b.user_id = $user_id
            DELETE r
            """
            
            await self.client.query(relationships_query, {"story_id": story_id, "user_id": user_id})
            
            # Delete all nodes
            nodes_query = """
            MATCH (n)
            WHERE n.story_id = $story_id AND n.user_id = $user_id
            DELETE n
            """
            
            result = await self.client.query(nodes_query, {"story_id": story_id, "user_id": user_id})
            
            return {
                "status": "success",
                "story_id": story_id,
                "deleted_at": datetime.utcnow().isoformat(),
                "message": f"Story {story_id} and all associated data deleted"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "story_id": story_id
            }
    
    # Helper methods for entity and relationship management
    
    async def upsert_entity(self, entity_type: str, properties: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create or update an entity in the knowledge graph.
        
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
            
            entity_node = EntityNode(
                name=properties.get("name", "Unknown"),
                labels=[entity_type],
                properties={
                    **final_properties,
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            await self.client.add_node(entity_node)
            
            return {
                "status": "success",
                "entity_type": entity_type,
                "entity_id": properties.get("id", properties.get("name")),
                "operation": "upserted"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "entity_type": entity_type
            }
    
    async def upsert_relationship(self, relationship_type: str, from_id: str, to_id: str, 
                                 properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a relationship in the knowledge graph.
        
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
            # Query to create or update relationship
            relationship_query = """
            MATCH (a), (b)
            WHERE a.id = $from_id AND b.id = $to_id
            MERGE (a)-[r:{relationship_type}]->(b)
            SET r += $properties
            SET r.updated_at = $timestamp
            RETURN r
            """.format(relationship_type=relationship_type)
            
            params = {
                "from_id": from_id,
                "to_id": to_id,
                "properties": properties,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            result = await self.client.query(relationship_query, params)
            
            return {
                "status": "success",
                "relationship_type": relationship_type,
                "from_id": from_id,
                "to_id": to_id,
                "operation": "upserted"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "relationship_type": relationship_type,
                "from_id": from_id,
                "to_id": to_id
            }
    
    async def execute_temporal_query(self, query: TemporalQuery) -> List[Dict[str, Any]]:
        """
        Execute a temporal query against the knowledge graph.
        
        Args:
            query: TemporalQuery object containing query parameters
            
        Returns:
            List of query results
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Build parametrized Cypher query with temporal constraints
            cypher_query = """
            MATCH (n)-[r]->(m)
            WHERE n.created_at <= $timestamp
            AND (n.valid_to IS NULL OR n.valid_to >= $timestamp)
            AND r.created_at <= $timestamp
            AND (r.valid_to IS NULL OR r.valid_to >= $timestamp)
            """
            
            params = {"timestamp": query.timestamp.isoformat()}
            
            # Add entity filters if provided
            if query.entity_filters:
                for key, value in query.entity_filters.items():
                    cypher_query += f" AND n.{key} = ${key}"
                    params[key] = value
            
            # Add relationship filters if provided
            if query.relationship_filters:
                for key, value in query.relationship_filters.items():
                    cypher_query += f" AND r.{key} = ${key}"
                    params[key] = value
            
            cypher_query += " RETURN n, r, m"
            
            results = await self.client.query(cypher_query, params)
            
            return [{"source": dict(r["n"]), "relationship": dict(r["r"]), "target": dict(r["m"])} 
                   for r in results]
            
        except Exception as e:
            raise RuntimeError(f"Failed to execute temporal query: {str(e)}")
    
    async def get_query_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph.
        
        Returns:
            Dict containing graph statistics
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            stats_query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]->()
            RETURN 
                count(DISTINCT n) as node_count,
                count(DISTINCT r) as relationship_count,
                count(DISTINCT n.story_id) as story_count
            """
            
            result = await self.client.query(stats_query)
            stats = result[0] if result else {}
            
            return {
                "node_count": stats.get("node_count", 0),
                "relationship_count": stats.get("relationship_count", 0),
                "story_count": stats.get("story_count", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
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
        self._story_sessions[story_id] = session_id
        
        # Initialize session in Graphiti - this would typically create episodic context
        await self.client.add_episode(
            name=f"Story Session: {story_id}",
            episode_body=f"Starting new story session for {story_id}",
            source_description=f"Story session initialization for {story_id}",
            reference_time=datetime.utcnow(),
            session_id=session_id
        )
        
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
                session_id=session_id,
                metadata=metadata or {}
            )
            
            return {
                "status": "success",
                "story_id": story_id,
                "session_id": session_id,
                "episode_id": episode_result.uuid if hasattr(episode_result, 'uuid') else None,
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
            # Use Graphiti's episode search to get recent context
            search_config = EpisodeSearchConfig(
                limit=limit
            )
            
            # Search for recent episodes in this session
            search_results = await self.client.search(
                query=f"story session {story_id}",
                config=search_config,
                session_id=session_id
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
            # Use Graphiti's episode search
            search_config = EpisodeSearchConfig(
                limit=limit
            )
            
            search_results = await self.client.search(
                query=query,
                config=search_config,
                session_id=session_id
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
            summary_results = await self.client.get_summary(
                session_id=self._story_sessions.get(story_id),
                summary_type="story_overview"
            )
            
            return summary_results.summary if hasattr(summary_results, 'summary') else "No summary available."
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    async def extract_facts(self, story_id: str, content: str) -> List[Dict[str, Any]]:
        """
        Extract facts from story content using Graphiti's fact extraction.
        
        Args:
            story_id: Story identifier
            content: Content to extract facts from
            
        Returns:
            List of extracted facts
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Use Graphiti's fact extraction capabilities
            facts = await self.client.extract_facts(
                content=content,
                session_id=self._story_sessions.get(story_id)
            )
            
            return [{
                "fact": fact.content,
                "entities": fact.entities,
                "confidence": fact.confidence,
                "timestamp": datetime.utcnow().isoformat()
            } for fact in facts]
            
        except Exception as e:
            print(f"Error extracting facts: {str(e)}")
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
        Get list of active story IDs for contradiction detection.
        
        Returns:
            List of story IDs that are currently active
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            # Query for all stories with recent activity (last 7 days)
            query = """
            MATCH (n)
            WHERE n.story_id IS NOT NULL
            AND n.updated_at >= datetime() - duration({days: 7})
            RETURN DISTINCT n.story_id as story_id
            ORDER BY n.updated_at DESC
            """
            
            results = await self.client.query(query)
            active_stories = [result["story_id"] for result in results]
            
            return active_stories
            
        except Exception as e:
            print(f"Error getting active stories: {str(e)}")
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
