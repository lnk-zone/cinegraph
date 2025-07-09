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
from graphiti_core.search.search_config import SearchConfig, EpisodeSearchConfig

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
                    "story_id": story_id
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
                    session_id=session_id
                )
                
                # Extract facts from the scene
                facts = await self.graphiti_manager.extract_facts(story_id, scene['text'])
                
                # Process extracted facts into entities and relationships
                scene_entities, scene_relationships, scene_knowledge = self._process_extracted_facts(
                    facts, scene, story_id, user_id
                )
                
                all_entities.extend(scene_entities)
                all_relationships.extend(scene_relationships)
                all_knowledge_items.extend(scene_knowledge)
                
                # Create scene entity
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
                        "episode_id": episode_result.uuid if hasattr(episode_result, 'uuid') else None,
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
                all_scenes.append(scene_entity)
                
            except Exception as e:
                print(f"Error processing scene {scene['id']}: {str(e)}")
                continue
        
        return {
            "entities": all_entities,
            "relationships": all_relationships,
            "scenes": all_scenes,
            "knowledge_items": all_knowledge_items
        }
    
    def _process_extracted_facts(self, facts: List[Dict[str, Any]], scene: Dict[str, Any], story_id: str, user_id: str) -> tuple:
        """
        Process extracted facts into entities, relationships, and knowledge items.
        
        Args:
            facts: List of extracted facts
            scene: Scene metadata
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Tuple of (entities, relationships, knowledge_items)
        """
        entities = []
        relationships = []
        knowledge_items = []
        
        for fact in facts:
            fact_entities = fact.get('entities', [])
            fact_content = fact.get('fact', '')
            confidence = fact.get('confidence', 0.5)
            
            # Create knowledge item
            knowledge_id = f"knowledge_{uuid.uuid4().hex[:8]}"
            knowledge_item = {
                "id": knowledge_id,
                "name": f"Knowledge: {fact_content[:50]}...",
                "type": "KNOWLEDGE",
                "properties": {
                    "content": fact_content,
                    "confidence": confidence,
                    "scene_id": scene['id'],
                    "story_id": story_id,
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            knowledge_items.append(knowledge_item)
            
            # Process entities mentioned in the fact
            for entity_name in fact_entities:
                entity_id = f"entity_{entity_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
                entity_type = self._determine_entity_type(entity_name, fact_content)
                
                entity = {
                    "id": entity_id,
                    "name": entity_name,
                    "type": entity_type,
                    "properties": {
                        "mentioned_in_scene": scene['id'],
                        "story_id": story_id,
                        "user_id": user_id,
                        "confidence": confidence,
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
                entities.append(entity)
                
                # Create relationship between entity and knowledge
                relationship = {
                    "type": "KNOWS",
                    "from_id": entity_id,
                    "to_id": knowledge_id,
                    "properties": {
                        "confidence": confidence,
                        "scene_id": scene['id'],
                        "story_id": story_id,
                        "user_id": user_id,
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
                relationships.append(relationship)
        
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
    
    def get_traceability_mapping(self, segment_id: str) -> Optional[str]:
        """
        Get scene_id for a given text segment.
        
        Args:
            segment_id: Text segment identifier
            
        Returns:
            Scene ID if found, None otherwise
        """
        return self._scene_mappings.get(segment_id)
