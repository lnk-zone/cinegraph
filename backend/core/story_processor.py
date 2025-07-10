"""
Story Processor Module
=====================

This module handles the processing of story content to extract entities,
relationships, and other structured data for the knowledge graph.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import uuid
import re
from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search import SearchConfig
from neo4j import AsyncGraphDatabase

from .graphiti_manager import GraphitiManager
from .models import EntityType, RelationshipType


class StoryProcessor:
    """
    Processes story content to extract structured data for the knowledge graph.
    Implements story ingestion pipeline with Graphiti's /extract endpoint.
    """
    
    def __init__(self, graphiti_manager: Optional[GraphitiManager] = None):
        """Initialize the story processor.
        
        Args:
            graphiti_manager: Optional GraphitiManager instance. If None, creates new one.
        """
        self.graphiti_manager = graphiti_manager or GraphitiManager()
        self._scene_mappings: Dict[str, str] = {}  # text_segment_id -> scene_id
        self._processing_stats = {
            "total_processed": 0,
            "avg_processing_time": 0,
            "last_processed": None
        }
    
    async def process_story(self, content: str, story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Process story content and extract structured data using Graphiti's extraction.
        
        Target: <300ms extraction for 2K words
        
        Args:
            content: Raw story content
            story_id: Unique story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing extracted entities, relationships, and metadata
        """
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Split content into manageable scenes/paragraphs
            scenes = self._split_into_scenes(content)
            
            # Step 2: Process each scene through Graphiti extraction
            extracted_data = await self._extract_with_graphiti(scenes, story_id, user_id)
            
            # Step 3: Map extraction output to schema and upsert
            await self._map_and_upsert_entities(extracted_data, story_id, user_id)
            
            # Step 4: Store traceability mappings
            self._store_traceability_mappings(scenes, extracted_data)
            
            # Step 5: Fix generic relationships (convert RELATES_TO, etc. to meaningful types)
            fix_results = await self._fix_generic_relationships(story_id)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update processing stats
            self._update_processing_stats(processing_time)
            
            return {
                "entities": extracted_data.get("entities", []),
                "relationships": extracted_data.get("relationships", []),
                "scenes": extracted_data.get("scenes", []),
                "knowledge_items": extracted_data.get("knowledge_items", []),
                "traceability_mappings": dict(self._scene_mappings),
                "metadata": {
                    "word_count": len(content.split()),
                    "scene_count": len(scenes),
                    "processing_time_ms": processing_time,
                    "processed_at": datetime.utcnow().isoformat(),
                    "processing_version": "1.0.0",
                    "story_id": story_id,
                    "scene_errors": extracted_data.get("scene_errors", []),  # Include scene errors
                    "relationship_fixes": fix_results  # Include relationship fixes
                }
            }
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "error": str(e),
                "processing_time_ms": processing_time,
                "processed_at": datetime.utcnow().isoformat(),
                "story_id": story_id
            }
    
    def _split_into_scenes(self, content: str) -> List[Dict[str, Any]]:
        """
        Split content into scenes/paragraphs for processing.
        
        Args:
            content: Raw story content
            
        Returns:
            List of scene dictionaries with metadata
        """
        # Split by double newlines or scene markers
        paragraphs = re.split(r'\n\s*\n|\n\s*---\s*\n|\n\s*\*\*\*\s*\n', content.strip())
        
        scenes = []
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if paragraph:  # Skip empty paragraphs
                scene_id = f"scene_{i+1}_{uuid.uuid4().hex[:8]}"
                scenes.append({
                    "id": scene_id,
                    "text": paragraph,
                    "order": i + 1,
                    "word_count": len(paragraph.split()),
                    "segment_id": f"segment_{i+1}"
                })
        
        return scenes
    
    async def _extract_with_graphiti(self, scenes: List[Dict[str, Any]], story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Extract entities, relations, and timestamps using Graphiti's capabilities.
        
        Args:
            scenes: List of scene dictionaries
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing extracted data
        """
        if not self.graphiti_manager.client:
            await self.graphiti_manager.connect()
        
        all_entities = []
        all_relationships = []
        all_scenes = []
        all_knowledge_items = []
        scene_errors = []  # Track errors for failed fact extraction
        
        # Get or create story session
        session_id = await self.graphiti_manager.create_story_session(story_id)
        
        for scene in scenes:
            try:
                # Use Graphiti's add_episode for extraction (acts as /extract endpoint)
                episode_result = await self.graphiti_manager.client.add_episode(
                    name=f"Scene {scene['order']} - {story_id}",
                    episode_body=scene['text'],
                    source_description=f"Scene {scene['order']} from story {story_id}",
                    reference_time=datetime.utcnow(),
                    group_id=session_id
                )
                
                # Capture the returned session_id from the episode for future calls
                if episode_result and hasattr(episode_result, 'group_id') and episode_result.group_id:
                    session_id = episode_result.group_id
                    # Update the session in the graphiti_manager
                    self.graphiti_manager._story_sessions[story_id] = session_id
                
                # Extract entities and relationships from Graphiti 0.3.0 - wrap in try/catch to prevent batch failure
                try:
                    # In Graphiti 0.3.0, add_episode automatically extracts entities/relationships
                    # We need to search for what was created to get the actual data
                    search_results = await self.graphiti_manager.client.search(
                        query=scene['text'][:100],  # Use first 100 chars as search query
                        group_ids=[session_id],
                        num_results=20  # Get more results to capture all extractions
                    )
                    
                    # Process search results to extract entities and relationships
                    scene_entities, scene_relationships, scene_knowledge = self._process_search_results(
                        search_results, scene, story_id, user_id
                    )
                    
                    all_entities.extend(scene_entities)
                    all_relationships.extend(scene_relationships)
                    all_knowledge_items.extend(scene_knowledge)
                    
                except Exception as extraction_error:
                    # Log extraction error but continue processing
                    error_info = {
                        "scene_id": scene['id'],
                        "error_type": "entity_extraction_failed",
                        "error_message": str(extraction_error),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    scene_errors.append(error_info)
                    print(f"Warning: Entity extraction failed for scene {scene['id']}: {str(extraction_error)}")
                
                # Create scene entity with defensive episode_id handling
                episode_id = None
                if episode_result:
                    # Try multiple possible attributes for the episode ID
                    for attr_name in ['uuid', 'id', 'episode_id']:
                        if hasattr(episode_result, attr_name):
                            episode_id = getattr(episode_result, attr_name)
                            break
                
                scene_entity = {
                    "id": scene['id'],
                    "name": f"Scene {scene['order']}",
                    "type": "SCENE",
                    "properties": {
                        "order": scene['order'],
                        "text": scene['text'],
                        "word_count": scene['word_count'],
                        "story_id": story_id,
                        "user_id": user_id,
                        "episode_id": episode_id,
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
                all_scenes.append(scene_entity)
                
            except Exception as e:
                # Log scene processing error but continue with other scenes
                error_info = {
                    "scene_id": scene['id'],
                    "error_type": "scene_processing_failed",
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                scene_errors.append(error_info)
                print(f"Warning: Scene processing failed for scene {scene['id']}: {str(e)}")
                continue
        
        return {
            "entities": all_entities,
            "relationships": all_relationships,
            "scenes": all_scenes,
            "knowledge_items": all_knowledge_items,
            "scene_errors": scene_errors  # Include errors in the result
        }
    
    def _process_search_results(self, search_results: List[Any], scene: Dict[str, Any], story_id: str, user_id: str) -> tuple:
        """
        Process search results from Graphiti 0.3.0 to extract entities, relationships, and knowledge items.
        
        Args:
            search_results: List of search results from Graphiti (EntityEdge, EntityNode, etc.)
            scene: Scene metadata
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Tuple of (entities, relationships, knowledge_items)
        """
        entities = []
        relationships = []
        knowledge_items = []
        
        for result in search_results:
            try:
                result_type = type(result).__name__
                
                if 'EntityEdge' in result_type:
                    # This is a relationship/edge
                    relationship_id = f"rel_{getattr(result, 'uuid', uuid.uuid4().hex[:8])}"
                    
                    relationship = {
                        "id": relationship_id,
                        "type": getattr(result, 'name', 'RELATED_TO'),
                        "from_id": getattr(result, 'source_node_uuid', 'unknown'),
                        "to_id": getattr(result, 'target_node_uuid', 'unknown'),
                        "properties": {
                            "fact": getattr(result, 'fact', ''),
                            "confidence": 0.8,  # Default confidence
                            "scene_id": scene['id'],
                            "story_id": story_id,
                            "user_id": user_id,
                            "created_at": getattr(result, 'created_at', datetime.utcnow()).isoformat() if hasattr(result, 'created_at') else datetime.utcnow().isoformat(),
                            "graphiti_uuid": getattr(result, 'uuid', None)
                        }
                    }
                    relationships.append(relationship)
                    
                    # Create knowledge item from the fact
                    if hasattr(result, 'fact') and result.fact:
                        knowledge_id = f"knowledge_{uuid.uuid4().hex[:8]}"
                        knowledge_item = {
                            "id": knowledge_id,
                            "name": f"Fact: {result.fact[:50]}...",
                            "type": "KNOWLEDGE",
                            "properties": {
                                "content": result.fact,
                                "confidence": 0.8,
                                "scene_id": scene['id'],
                                "story_id": story_id,
                                "user_id": user_id,
                                "created_at": datetime.utcnow().isoformat(),
                                "source_relationship": relationship_id
                            }
                        }
                        knowledge_items.append(knowledge_item)
                
                elif 'EntityNode' in result_type or 'Node' in result_type:
                    # This is an entity/node
                    entity_id = f"entity_{getattr(result, 'uuid', uuid.uuid4().hex[:8])}"
                    entity_name = getattr(result, 'name', 'Unknown Entity')
                    entity_type = self._determine_entity_type(entity_name, getattr(result, 'summary', ''))
                    
                    entity = {
                        "id": entity_id,
                        "name": entity_name,
                        "type": entity_type,
                        "properties": {
                            "summary": getattr(result, 'summary', ''),
                            "mentioned_in_scene": scene['id'],
                            "story_id": story_id,
                            "user_id": user_id,
                            "confidence": 0.8,
                            "created_at": getattr(result, 'created_at', datetime.utcnow()).isoformat() if hasattr(result, 'created_at') else datetime.utcnow().isoformat(),
                            "graphiti_uuid": getattr(result, 'uuid', None)
                        }
                    }
                    entities.append(entity)
                
            except Exception as e:
                print(f"Warning: Error processing search result {result_type}: {str(e)}")
                continue
        
        return entities, relationships, knowledge_items
    
    def _determine_entity_type(self, entity_name: str, context: str) -> str:
        """
        Determine the type of an entity based on name and context.
        
        Args:
            entity_name: Name of the entity
            context: Context where entity appears
            
        Returns:
            Entity type string
        """
        entity_name_lower = entity_name.lower()
        context_lower = context.lower()
        
        # Simple heuristics for entity type determination
        if any(word in entity_name_lower for word in ['castle', 'town', 'forest', 'mountain', 'river', 'room', 'house']):
            return "LOCATION"
        elif any(word in context_lower for word in ['said', 'told', 'spoke', 'thought', 'felt', 'character']):
            return "CHARACTER"
        elif any(word in entity_name_lower for word in ['sword', 'potion', 'key', 'ring', 'book', 'scroll']):
            return "ITEM"
        elif any(word in context_lower for word in ['happened', 'occurred', 'event', 'battle', 'meeting']):
            return "EVENT"
        else:
            return "CHARACTER"  # Default to character
    
    async def _map_and_upsert_entities(self, extracted_data: Dict[str, Any], story_id: str, user_id: str) -> None:
        """
        Map extracted data to schema and upsert using GraphitiManager.
        
        Args:
            extracted_data: Extracted entities and relationships
            story_id: Story identifier
            user_id: User ID for data isolation
        """
        # Upsert entities
        for entity in extracted_data.get("entities", []):
            await self.graphiti_manager.upsert_entity(
                entity_type=entity["type"],
                properties={
                    "id": entity["id"],
                    "name": entity["name"],
                    **entity["properties"]
                }
            )
        
        # Upsert scenes
        for scene in extracted_data.get("scenes", []):
            await self.graphiti_manager.upsert_entity(
                entity_type="SCENE",
                properties={
                    "id": scene["id"],
                    "name": scene["name"],
                    **scene["properties"]
                }
            )
        
        # Upsert knowledge items
        for knowledge in extracted_data.get("knowledge_items", []):
            await self.graphiti_manager.upsert_entity(
                entity_type="KNOWLEDGE",
                properties={
                    "id": knowledge["id"],
                    "name": knowledge["name"],
                    **knowledge["properties"]
                }
            )
        
        # Upsert relationships
        for relationship in extracted_data.get("relationships", []):
            await self.graphiti_manager.upsert_relationship(
                relationship_type=relationship["type"],
                from_id=relationship["from_id"],
                to_id=relationship["to_id"],
                properties=relationship["properties"]
            )
    
    def _store_traceability_mappings(self, scenes: List[Dict[str, Any]], extracted_data: Dict[str, Any]) -> None:
        """
        Store mapping from original text segment to scene_id for traceability.
        
        Args:
            scenes: Original scene data
            extracted_data: Extracted data with scene entities
        """
        for scene in scenes:
            segment_id = scene["segment_id"]
            scene_id = scene["id"]
            self._scene_mappings[segment_id] = scene_id
        
        # Also map any additional entities to their source scenes
        for entity in extracted_data.get("entities", []):
            if "mentioned_in_scene" in entity.get("properties", {}):
                entity_id = entity["id"]
                scene_id = entity["properties"]["mentioned_in_scene"]
                self._scene_mappings[f"entity_{entity_id}"] = scene_id
    
    def _update_processing_stats(self, processing_time: float) -> None:
        """
        Update processing statistics.
        
        Args:
            processing_time: Processing time in milliseconds
        """
        self._processing_stats["total_processed"] += 1
        total = self._processing_stats["total_processed"]
        current_avg = self._processing_stats["avg_processing_time"]
        
        # Calculate new running average
        self._processing_stats["avg_processing_time"] = ((current_avg * (total - 1)) + processing_time) / total
        self._processing_stats["last_processed"] = datetime.utcnow().isoformat()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get current processing statistics.
        
        Returns:
            Dict containing processing statistics
        """
        return dict(self._processing_stats)
    
    async def _fix_generic_relationships(self, story_id: str) -> Dict[str, Any]:
        """
        Post-process relationships to convert generic types to meaningful names.
        This addresses the Graphiti 0.3.0 issue where relationships are created with
        generic types (RELATES_TO, MENTIONS, HAS_MEMBER) but meaningful names are
        stored in the 'name' property.
        
        Args:
            story_id: Story identifier to limit the scope of fixes
            
        Returns:
            Dict containing fix results
        """
        if not self.graphiti_manager.client:
            return {"status": "error", "error": "No client connection"}
        
        # Generic relationship types that need conversion
        GENERIC_TYPES = ['RELATES_TO', 'MENTIONS', 'HAS_MEMBER']
        
        # Get connection details from GraphitiManager
        config = self.graphiti_manager.config
        driver = AsyncGraphDatabase.driver(
            config.database_url, 
            auth=(config.username, config.password)
        )
        
        try:
            async with driver.session() as session:
                total_fixed = 0
                fix_results = []
                
                for generic_type in GENERIC_TYPES:
                    # Find relationships of this type that need fixing
                    result = await session.run(f"""
                        MATCH ()-[r:{generic_type}]->()
                        WHERE r.name IS NOT NULL AND r.name <> type(r)
                        AND (r.group_id CONTAINS $story_id OR r.story_id = $story_id)
                        RETURN r.name as meaningful_name, count(*) as count
                    """, story_id=story_id)
                    
                    relationships_to_fix = []
                    async for record in result:
                        meaningful_name = record['meaningful_name']
                        count = record['count']
                        relationships_to_fix.append((meaningful_name, count))
                    
                    # Fix each meaningful relationship type
                    for meaningful_name, count in relationships_to_fix:
                        if count == 0:
                            continue
                            
                        # Sanitize the relationship name for Neo4j
                        safe_name = meaningful_name.upper().replace(' ', '_').replace('-', '_')
                        
                        try:
                            # Convert relationships
                            fix_result = await session.run(f"""
                                MATCH (a)-[old:{generic_type}]->(b)
                                WHERE old.name = $meaningful_name
                                AND (old.group_id CONTAINS $story_id OR old.story_id = $story_id)
                                WITH a, old, b, old {{ .* }} as props
                                DELETE old
                                CREATE (a)-[new:{safe_name}]->(b)
                                SET new = props
                                RETURN count(new) as converted
                            """, meaningful_name=meaningful_name, story_id=story_id)
                            
                            record = await fix_result.single()
                            converted = record['converted'] if record else 0
                            total_fixed += converted
                            
                            if converted > 0:
                                fix_results.append({
                                    "from_type": generic_type,
                                    "to_type": safe_name,
                                    "converted": converted,
                                    "original_name": meaningful_name
                                })
                                
                        except Exception as e:
                            print(f"Warning: Error fixing {generic_type}->{meaningful_name}: {e}")
                            continue
                
                return {
                    "status": "success",
                    "total_fixed": total_fixed,
                    "fixes": fix_results,
                    "story_id": story_id
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "story_id": story_id
            }
        finally:
            await driver.close()
    
    def get_traceability_mapping(self, segment_id: str) -> Optional[str]:
        """
        Get scene_id for a given text segment.
        
        Args:
            segment_id: Text segment identifier
            
        Returns:
            Scene ID if found, None otherwise
        """
        return self._scene_mappings.get(segment_id)
