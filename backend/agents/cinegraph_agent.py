"""
CineGraph Agent Module
=====================

This module provides the CineGraph AI agent interface for story analysis,
querying, and consistency validation.
"""

import asyncio
import json
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from openai import AsyncOpenAI
from core.redis_alerts import alert_manager
from core.models import TemporalQuery
from supabase import create_client, Client

from .query_tools import GraphQueryTools
from .alert_manager import AlertManager
from .story_analysis_agent import StoryAnalysisAgent


class DialoguePatternExtractor:
    """
    Extracts dialogue patterns from episodic search results.
    """
    
    def __init__(self, search_results):
        self.search_results = search_results
        
    def extract_patterns(self) -> List[Dict[str, Any]]:
        """Extract dialogue patterns from search results."""
        patterns = []
        
        for result in self.search_results:
            content = getattr(result, 'episode_body', '')
            if 'dialogue' in content.lower() or 'said' in content.lower():
                # Simple pattern extraction - look for character mentions
                characters = self._extract_characters(content)
                if len(characters) >= 2:
                    for i, char1 in enumerate(characters):
                        for char2 in characters[i+1:]:
                            patterns.append({
                                "character_1": char1,
                                "character_2": char2,
                                "interaction_type": "dialogue",
                                "content": content,
                                "timestamp": getattr(result, 'created_at', None)
                            })
        
        return patterns
    
    def _extract_characters(self, content: str) -> List[str]:
        """Extract character names from content using simple heuristics."""
        import re
        # Look for capitalized words that might be character names
        character_pattern = r'\b[A-Z][a-z]+\b'
        potential_chars = re.findall(character_pattern, content)
        
        # Filter common words that aren't character names
        common_words = {'The', 'And', 'But', 'For', 'Not', 'With', 'He', 'She', 'They', 'Story', 'Episode'}
        characters = [char for char in potential_chars if char not in common_words]
        
        return list(set(characters))  # Remove duplicates


class InteractionStrengthExtractor:
    """
    Calculates relationship strengths from dialogue patterns.
    """
    
    def __init__(self, dialogue_patterns):
        self.dialogue_patterns = dialogue_patterns
        
    def calculate_strengths(self) -> Dict[Tuple[str, str], int]:
        """Calculate interaction strengths between character pairs."""
        strengths = {}
        
        for pattern in self.dialogue_patterns:
            char1 = pattern["character_1"]
            char2 = pattern["character_2"]
            
            # Create bidirectional strength tracking
            pair = tuple(sorted([char1, char2]))
            
            if pair not in strengths:
                strengths[pair] = 0
            
            # Increment strength based on interaction type
            if pattern["interaction_type"] == "dialogue":
                strengths[pair] += 2  # Dialogue interactions are strong
            else:
                strengths[pair] += 1  # Other interactions are weaker
        
        return strengths


class SNARelationshipExtractor:
    """
    Generates SNA-ready relationships with proper metrics for Neo4j graph algorithms.
    """
    
    def __init__(self, relationship_strengths):
        self.relationship_strengths = relationship_strengths
        
    def generate_sna_relationships(self) -> List[Dict[str, Any]]:
        """Generate relationships optimized for SNA algorithms."""
        relationships = []
        
        for (char1, char2), strength in self.relationship_strengths.items():
            # Determine relationship type based on strength
            rel_type = self._determine_relationship_type(strength)
            
            # Calculate confidence based on interaction frequency
            confidence = min(strength / 20.0, 1.0)  # Scale to 0-1
            
            # Create bidirectional relationships for SNA
            relationships.extend([
                {
                    "from_character": char1,
                    "to_character": char2,
                    "type": rel_type,
                    "strength": strength,
                    "confidence": confidence,
                    "bidirectional": True,
                    "sna_weight": strength,  # For centrality calculations
                    "trust_level": min(strength // 2, 10),  # Trust correlates with interaction
                    "relationship_status": "current"
                },
                {
                    "from_character": char2,
                    "to_character": char1,
                    "type": rel_type,
                    "strength": strength,
                    "confidence": confidence,
                    "bidirectional": True,
                    "sna_weight": strength,
                    "trust_level": min(strength // 2, 10),
                    "relationship_status": "current"
                }
            ])
        
        return relationships
    
    def _determine_relationship_type(self, strength: int) -> str:
        """Determine relationship type based on interaction strength."""
        if strength >= 15:
            return "FRIENDS_WITH"  # Strong positive relationship
        elif strength >= 8:
            return "KNOWS"  # Moderate relationship
        elif strength >= 3:
            return "ACQUAINTED_WITH"  # Weak relationship
        else:
            return "MENTIONED_WITH"  # Very weak relationship


class CineGraphAgent(StoryAnalysisAgent, AlertManager, GraphQueryTools):
    """
    AI-powered agent for story consistency validation, querying, and analysis.
    Enhanced with advanced Cypher capabilities, query optimization, and schema awareness.
    """
    
    def __init__(self, graphiti_manager=None, openai_api_key: str = None, supabase_url: str = None, supabase_key: str = None):
        self.graphiti_manager = graphiti_manager
        
        # Initialize OpenAI client if API key is provided
        if openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        else:
            self.openai_client = None
            
        # Initialize Supabase client if URL and key are provided
        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
        else:
            self.supabase = None
            
        self.model = "gpt-4-turbo-preview"
        
        # Enhanced capabilities
        self.schema_context = self._load_schema_context()
        self.query_cache = {}  # Cache for frequently used queries
        self.query_templates = self._build_query_templates()
        # TODO: Update current_owner field on ItemEntity when new OWNS relationships are created or ended.
        self.dangerous_operations = {'DELETE', 'DROP', 'CREATE', 'MERGE', 'SET', 'REMOVE', 'DETACH'}
        
        self.system_prompt = self._build_enhanced_system_prompt()
        self.tool_schemas = self._build_enhanced_tool_schemas()
        self._setup_redis_alerts()
    
    def _load_schema_context(self) -> Dict[str, Any]:
        """Load and parse the complete CineGraph schema for enhanced query generation."""
        
        # Define enum values for schema validation
        enums = {
            "knowledge_type": ["factual", "relationship", "emotional", "social", "secret"],
            "importance_level": ["critical", "important", "minor"],
            "verification_status": ["confirmed", "suspected", "false", "unknown"],
            "location_type": ["city", "building", "room", "outdoor"],
            "accessibility": ["public", "private", "restricted", "secret"],
            "participation_level": ["active", "passive", "mentioned", "background"],
            "relationship_type": ["family", "friend", "enemy", "ally", "romantic", "professional", "stranger"],
            "emotional_valence": ["love", "like", "neutral", "dislike", "hate"],
            "relationship_status": ["current", "past", "complicated", "unknown"],
            "power_dynamic": ["equal", "dominant", "submissive", "complex"],
            "confidence_level": ["certain", "probable", "suspected", "rumored"],
            "sharing_restrictions": ["can_share", "must_keep_secret", "conditional_sharing"],
            "emotional_impact": ["positive", "negative", "neutral", "shocking"],
            "contradiction_type": ["factual", "temporal", "logical", "character_behavior"],
            "severity": ["critical", "major", "minor", "potential"],
            "resolution_status": ["unresolved", "resolved", "false_positive", "ignored"],
            "implication_strength": ["certain", "probable", "possible", "weak"],
            "location_accessibility": ["public", "private", "restricted", "secret"]
        }
        
        schema = {
            "enums": enums,
            "entities": [
                {
                    "name": "Character",
                    "description": "Represents individual characters in the story",
                    "properties": {
                        "character_id": {"type": "string", "unique": True, "required": True},
                        "name": {"type": "string", "required": True},
                        "aliases": {"type": "array", "items": "string"},
                        "description": {"type": "string"},
                        "role": {"type": "string"},
                        "first_appearance": {"type": "timestamp"},
                        "last_mentioned": {"type": "timestamp"},
                        "is_active": {"type": "boolean", "default": True},
                        "story_id": {"type": "string", "required": True},
                        "user_id": {"type": "string", "required": True},
                        # Temporal properties
                        "valid_from": {"type": "timestamp", "temporal": True},
                        "valid_to": {"type": "timestamp", "temporal": True},
                        "created_at": {"type": "timestamp", "temporal": True},
                        "updated_at": {"type": "timestamp", "temporal": True},
                        "deleted_at": {"type": "timestamp", "temporal": True}
                    }
                },
                {
                    "name": "Knowledge",
                    "description": "Represents discrete pieces of information that characters can possess",
                    "properties": {
                        "knowledge_id": {"type": "string", "unique": True, "required": True},
                        "content": {"type": "string", "required": True},
                        "knowledge_type": {"type": "enum", "values": enums["knowledge_type"]},
                        "importance_level": {"type": "enum", "values": enums["importance_level"]},
                        "source_scene": {"type": "string"},
                        "is_secret": {"type": "boolean", "default": False},
                        "verification_status": {"type": "enum", "values": enums["verification_status"]},
                        "story_id": {"type": "string", "required": True},
                        "user_id": {"type": "string", "required": True},
                        # Temporal properties
                        "valid_from": {"type": "timestamp", "temporal": True},
                        "valid_to": {"type": "timestamp", "temporal": True},
                        "created_at": {"type": "timestamp", "temporal": True},
                        "updated_at": {"type": "timestamp", "temporal": True}
                    }
                },
                {
                    "name": "Scene",
                    "description": "Represents narrative scenes or story segments",
                    "properties": {
                        "scene_id": {"type": "string", "unique": True, "required": True},
                        "title": {"type": "string"},
                        "content": {"type": "text"},
                        "scene_order": {"type": "integer", "sequential": True, "required": True},
                        "timestamp_in_story": {"type": "timestamp"},
                        "location": {"type": "string"},
                        "characters_present": {"type": "array", "items": "string"},
                        "word_count": {"type": "integer"},
                        "story_id": {"type": "string", "required": True},
                        "user_id": {"type": "string", "required": True},
                        # Temporal properties
                        "valid_from": {"type": "timestamp", "temporal": True},
                        "valid_to": {"type": "timestamp", "temporal": True},
                        "created_at": {"type": "timestamp", "temporal": True},
                        "updated_at": {"type": "timestamp", "temporal": True}
                    }
                },
                {
                    "name": "Location",
                    "description": "Represents places where story events occur",
                    "properties": {
                        "location_id": {"type": "string", "unique": True, "required": True},
                        "name": {"type": "string", "required": True},
                        "description": {"type": "string"},
                        "location_type": {"type": "enum", "values": enums["location_type"]},
                        "accessibility": {"type": "enum", "values": enums["accessibility"]},
                        "first_mentioned": {"type": "timestamp"},
                        "is_active": {"type": "boolean", "default": True},
                        "story_id": {"type": "string", "required": True},
                        "user_id": {"type": "string", "required": True},
                        # Temporal properties
                        "valid_from": {"type": "timestamp", "temporal": True},
                        "valid_to": {"type": "timestamp", "temporal": True},
                        "created_at": {"type": "timestamp", "temporal": True},
                        "updated_at": {"type": "timestamp", "temporal": True}
                    }
                }
            ],
            "relationships": [
                {
                    "type": "KNOWS",
                    "description": "Connects characters to knowledge they possess",
                    "from": "Character",
                    "to": "Knowledge",
                    "properties": {
                        "learned_at": {"type": "timestamp", "required": True},
                        "learned_from": {"type": "string"},
                        "confidence_level": {"type": "enum", "values": enums["confidence_level"]},
                        "knowledge_context": {"type": "string"},
                        "is_current": {"type": "boolean", "default": True},
                        "sharing_restrictions": {"type": "enum", "values": enums["sharing_restrictions"]},
                        "emotional_impact": {"type": "enum", "values": enums["emotional_impact"]},
                        "story_id": {"type": "string", "required": True},
                        "user_id": {"type": "string", "required": True},
                        # Temporal properties
                        "valid_from": {"type": "timestamp", "temporal": True},
                        "valid_to": {"type": "timestamp", "temporal": True},
                        "created_at": {"type": "timestamp", "temporal": True},
                        "updated_at": {"type": "timestamp", "temporal": True}
                    }
                },
                {
                    "type": "RELATIONSHIP",
                    "description": "Connects characters to other characters with relationship context",
                    "from": "Character",
                    "to": "Character",
                    "properties": {
                        "relationship_type": {"type": "enum", "values": enums["relationship_type"], "required": True},
                        "relationship_strength": {"type": "integer", "min": 1, "max": 10},
                        "trust_level": {"type": "integer", "min": 1, "max": 10},
                        "emotional_valence": {"type": "enum", "values": enums["emotional_valence"]},
                        "relationship_status": {"type": "enum", "values": enums["relationship_status"]},
                        "established_at": {"type": "timestamp"},
                        "last_interaction": {"type": "timestamp"},
                        "is_mutual": {"type": "boolean", "default": True},
                        "relationship_context": {"type": "string"},
                        "power_dynamic": {"type": "enum", "values": enums["power_dynamic"]},
                        "story_id": {"type": "string", "required": True},
                        "user_id": {"type": "string", "required": True},
                        # Temporal properties
                        "valid_from": {"type": "timestamp", "temporal": True},
                        "valid_to": {"type": "timestamp", "temporal": True},
                        "created_at": {"type": "timestamp", "temporal": True},
                        "updated_at": {"type": "timestamp", "temporal": True}
                    }
                },
                {
                    "type": "PRESENT_IN",
                    "description": "Connects characters to scenes where they appear",
                    "from": "Character",
                    "to": "Scene",
                    "properties": {
                        "arrival_time": {"type": "timestamp"},
                        "departure_time": {"type": "timestamp"},
                        "participation_level": {"type": "enum", "values": enums["participation_level"]},
                        "character_state": {"type": "string"},
                        "dialogue_count": {"type": "integer", "min": 0},
                        "actions_performed": {"type": "array", "items": "string"},
                        "story_id": {"type": "string", "required": True},
                        "user_id": {"type": "string", "required": True},
                        # Temporal properties
                        "created_at": {"type": "timestamp", "temporal": True},
                        "updated_at": {"type": "timestamp", "temporal": True}
                    }
                },
                {
                    "type": "OCCURS_IN",
                    "description": "Connects scenes to locations where they take place",
                    "from": "Scene",
                    "to": "Location",
                    "properties": {
                        "scene_duration": {"type": "string"},
                        "time_of_day": {"type": "string"},
                        "weather_conditions": {"type": "string"},
                        "location_accessibility": {"type": "enum", "values": enums["location_accessibility"]},
                        "story_id": {"type": "string", "required": True},
                        "user_id": {"type": "string", "required": True},
                        # Temporal properties
                        "created_at": {"type": "timestamp", "temporal": True}
                    }
                },
                {
                    "type": "CONTRADICTS",
                    "description": "Connects knowledge items that are inconsistent with each other",
                    "from": "Knowledge",
                    "to": "Knowledge",
                    "properties": {
                        "contradiction_type": {"type": "enum", "values": enums["contradiction_type"]},
                        "severity": {"type": "enum", "values": enums["severity"]},
                        "detected_at": {"type": "timestamp"},
                        "resolution_status": {"type": "enum", "values": enums["resolution_status"]},
                        "resolution_notes": {"type": "string"},
                        "story_id": {"type": "string", "required": True},
                        "user_id": {"type": "string", "required": True},
                        # Temporal properties
                        "created_at": {"type": "timestamp", "temporal": True},
                        "updated_at": {"type": "timestamp", "temporal": True}
                    }
                },
                {
                    "type": "IMPLIES",
                    "description": "Connects knowledge items where one logically implies another",
                    "from": "Knowledge",
                    "to": "Knowledge",
                    "properties": {
                        "implication_strength": {"type": "enum", "values": enums["implication_strength"]},
                        "logical_basis": {"type": "string"},
                        "story_id": {"type": "string", "required": True},
                        "user_id": {"type": "string", "required": True},
                        # Temporal properties
                        "created_at": {"type": "timestamp", "temporal": True},
                        "updated_at": {"type": "timestamp", "temporal": True}
                    }
                }
            ],
            "validation_rules": {
                "entity_validation": [
                    "Every Character must have a unique name within a project",
                    "Knowledge content cannot be empty or null",
                    "Scene order must be sequential and unique",
                    "Location names must be unique within a project"
                ],
                "relationship_validation": [
                    "KNOWS relationships require valid character_id and knowledge_id",
                    "RELATIONSHIP relationships cannot connect a character to themselves",
                    "PRESENT_IN relationships require valid character_id and scene_id",
                    "Temporal properties must be logically consistent (valid_from <= valid_to)"
                ],
                "consistency_rules": [
                    "Characters cannot know information before it exists in the story timeline",
                    "Characters cannot be present in scenes that occur before their first appearance",
                    "Contradictory knowledge items must be flagged for resolution",
                    "Relationship changes must be temporally consistent"
                ]
            }
        }
        return schema
    
    def _build_query_templates(self) -> Dict[str, str]:
        """Build reusable Cypher query templates for enhanced schema operations."""
        return {
            # Enhanced Character Knowledge Queries
            "character_knowledge_at_time": """
                MATCH (c:Character {name: $character_name, story_id: $story_id})-[knows:KNOWS]->(k:Knowledge)
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                AND k.valid_from <= $timestamp
                AND (k.valid_to IS NULL OR k.valid_to >= $timestamp)
                RETURN k, knows.learned_at, knows.confidence_level, knows.emotional_impact
                ORDER BY k.valid_from DESC
            """,
            
            # Enhanced Scene Analysis
            "characters_in_scene": """
                MATCH (c:Character)-[present:PRESENT_IN]->(s:Scene {scene_id: $scene_id, story_id: $story_id})
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                RETURN c, present.participation_level, present.dialogue_count, present.character_state
                ORDER BY c.name
            """,
            
            "scene_location_details": """
                MATCH (s:Scene {scene_id: $scene_id, story_id: $story_id})-[occurs:OCCURS_IN]->(l:Location)
                WHERE ($user_id IS NULL OR s.user_id = $user_id)
                RETURN l, occurs.time_of_day, occurs.weather_conditions, occurs.scene_duration
            """,
            
            # Enhanced Relationship Analysis
            "character_relationships_detailed": """
                MATCH (c1:Character {name: $character_name, story_id: $story_id})-[r:RELATIONSHIP]->(c2:Character)
                WHERE ($user_id IS NULL OR c1.user_id = $user_id)
                RETURN c2, r.relationship_type, r.relationship_strength, r.trust_level, 
                       r.emotional_valence, r.relationship_status, r.power_dynamic
                ORDER BY r.relationship_strength DESC, r.created_at DESC
            """,
            
            # Knowledge Analysis with Enhanced Properties
            "knowledge_by_type": """
                MATCH (k:Knowledge {story_id: $story_id})
                WHERE ($user_id IS NULL OR k.user_id = $user_id)
                AND ($knowledge_type IS NULL OR k.knowledge_type = $knowledge_type)
                AND ($importance_level IS NULL OR k.importance_level = $importance_level)
                RETURN k, k.knowledge_type, k.importance_level, k.verification_status
                ORDER BY k.importance_level, k.created_at DESC
            """,
            
            # Secret Knowledge Detection
            "secret_knowledge": """
                MATCH (c:Character {story_id: $story_id})-[knows:KNOWS]->(k:Knowledge)
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                AND k.is_secret = true
                AND knows.sharing_restrictions IN ['must_keep_secret', 'conditional_sharing']
                RETURN c, k, knows.sharing_restrictions, knows.emotional_impact
                ORDER BY k.importance_level DESC
            """,
            
            # Temporal Knowledge Conflicts with Enhanced Detection
            "temporal_knowledge_conflicts": """
                MATCH (c:Character {story_id: $story_id})-[:KNOWS]->(k1:Knowledge)
                MATCH (c)-[:KNOWS]->(k2:Knowledge)
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                AND k1.knowledge_id <> k2.knowledge_id
                AND k1.valid_from > k2.valid_to
                AND NOT EXISTS((k1)-[:CONTRADICTS]->(k2))
                RETURN c, k1, k2, k1.importance_level as k1_importance, k2.importance_level as k2_importance
                ORDER BY k1.importance_level DESC
            """,
            
            # Tier-2 Templates for Relationship Milestones and Plot Thread Resolution
            "relationship_milestones_over_time": """
                MATCH (c1:Character)-[r:RELATIONSHIP]-(c2:Character)
                WHERE c1.name = $character_a AND c2.name = $character_b AND c1.story_id = $story_id
                AND ($user_id IS NULL OR c1.user_id = $user_id)
                AND (r.established_at BETWEEN $start_time AND $end_time OR r.updated_at BETWEEN $start_time AND $end_time)
                RETURN r.relationship_type, r.relationship_strength, r.trust_level, r.emotional_valence, 
                       r.power_dynamic, r.established_at, r.updated_at, r.last_interaction
                ORDER BY r.updated_at ASC
            """,
            
            "plot_thread_resolution_status": """
                MATCH (k:Knowledge {story_id: $story_id})
                WHERE ($user_id IS NULL OR k.user_id = $user_id)
                AND ($verification_status IS NULL OR k.verification_status = $verification_status)
                OPTIONAL MATCH (k)-[contradicts:CONTRADICTS]-(other:Knowledge)
                RETURN k.content, k.source_scene, k.verification_status, k.updated_at, k.importance_level,
                       collect(DISTINCT {contradiction: other.content, severity: contradicts.severity, 
                                       resolution_status: contradicts.resolution_status}) as related_contradictions
                ORDER BY k.importance_level DESC, k.updated_at DESC
            """,
            
            # Enhanced Story Timeline
            "story_timeline_detailed": """
                MATCH (s:Scene {story_id: $story_id})
                WHERE ($user_id IS NULL OR s.user_id = $user_id)
                OPTIONAL MATCH (s)-[occurs:OCCURS_IN]->(l:Location)
                OPTIONAL MATCH (c:Character)-[present:PRESENT_IN]->(s)
                RETURN s, l, occurs.time_of_day, occurs.weather_conditions, 
                       collect(DISTINCT {character: c.name, participation: present.participation_level}) as characters
                ORDER BY s.scene_order ASC
            """,
            
            # Knowledge Propagation with Strength Analysis
            "knowledge_propagation": """
                MATCH (k1:Knowledge {story_id: $story_id})-[implies:IMPLIES]->(k2:Knowledge)
                WHERE ($user_id IS NULL OR k1.user_id = $user_id)
                RETURN k1, k2, implies.implication_strength, implies.logical_basis
                ORDER BY implies.implication_strength DESC, k1.created_at
            """,
            
            # Contradiction Detection with Severity
            "contradictions_by_severity": """
                MATCH (k1:Knowledge {story_id: $story_id})-[contradicts:CONTRADICTS]->(k2:Knowledge)
                WHERE ($user_id IS NULL OR k1.user_id = $user_id)
                AND ($severity IS NULL OR contradicts.severity = $severity)
                AND contradicts.resolution_status = 'unresolved'
                RETURN k1, k2, contradicts.severity, contradicts.contradiction_type, 
                       contradicts.detected_at, contradicts.resolution_notes
                ORDER BY 
                    CASE contradicts.severity 
                        WHEN 'critical' THEN 1
                        WHEN 'major' THEN 2
                        WHEN 'minor' THEN 3
                        WHEN 'potential' THEN 4
                        ELSE 5
                    END,
                    contradicts.detected_at DESC
            """,
            
            # Character Activity Analysis
            "character_activity_timeline": """
                MATCH (c:Character {name: $character_name, story_id: $story_id})
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                OPTIONAL MATCH (c)-[present:PRESENT_IN]->(s:Scene)
                OPTIONAL MATCH (c)-[knows:KNOWS]->(k:Knowledge)
                RETURN c, 
                       collect(DISTINCT {scene: s.title, order: s.scene_order, participation: present.participation_level}) as scenes,
                       collect(DISTINCT {knowledge: k.content, learned_at: knows.learned_at, confidence: knows.confidence_level}) as knowledge
                ORDER BY c.first_appearance
            """,
            
            # Location Accessibility Analysis
            "location_accessibility": """
                MATCH (l:Location {story_id: $story_id})
                WHERE ($user_id IS NULL OR l.user_id = $user_id)
                AND ($accessibility IS NULL OR l.accessibility = $accessibility)
                OPTIONAL MATCH (s:Scene)-[occurs:OCCURS_IN]->(l)
                RETURN l, l.accessibility, l.location_type, count(s) as scene_count
                ORDER BY l.accessibility, scene_count DESC
            """,
            
            # Relationship Strength Analysis
            "relationship_strength_analysis": """
                MATCH (c1:Character {story_id: $story_id})-[r:RELATIONSHIP]->(c2:Character)
                WHERE ($user_id IS NULL OR c1.user_id = $user_id)
                AND ($min_strength IS NULL OR r.relationship_strength >= $min_strength)
                RETURN c1, c2, r.relationship_type, r.relationship_strength, r.trust_level, 
                       r.emotional_valence, r.is_mutual
                ORDER BY r.relationship_strength DESC, r.trust_level DESC
            """,
            
            # Character Trust Network
            "character_trust_network": """
                MATCH (c1:Character {story_id: $story_id})-[r:RELATIONSHIP]->(c2:Character)
                WHERE ($user_id IS NULL OR c1.user_id = $user_id)
                AND r.trust_level >= $min_trust_level
                RETURN c1, c2, r.trust_level, r.relationship_type, r.established_at
                ORDER BY r.trust_level DESC
            """,
            
            # Knowledge Sharing Analysis
            "knowledge_sharing_patterns": """
                MATCH (c1:Character {story_id: $story_id})-[knows:KNOWS]->(k:Knowledge)
                MATCH (c2:Character {story_id: $story_id})-[knows2:KNOWS]->(k)
                WHERE ($user_id IS NULL OR c1.user_id = $user_id)
                AND c1.character_id <> c2.character_id
                AND knows.learned_at < knows2.learned_at
                RETURN c1, c2, k, knows.learned_at as first_learned, knows2.learned_at as second_learned,
                       knows.sharing_restrictions, knows2.learned_from
                ORDER BY knows.learned_at
            """,
            
            # Scene Participation Analysis
            "scene_participation_analysis": """
                MATCH (s:Scene {story_id: $story_id})
                WHERE ($user_id IS NULL OR s.user_id = $user_id)
                OPTIONAL MATCH (c:Character)-[present:PRESENT_IN]->(s)
                RETURN s, s.scene_order, s.word_count,
                       collect({
                           character: c.name,
                           participation: present.participation_level,
                           dialogue_count: present.dialogue_count,
                           state: present.character_state
                       }) as participants
                ORDER BY s.scene_order
            """
        }
    
    def _build_enhanced_system_prompt(self) -> str:
        """Build enhanced system prompt with comprehensive schema and capabilities."""
        schema_json = json.dumps(self.schema_context, indent=2)
        
        return f"""
        You are CineGraphAgent, an advanced AI assistant specialized in story analysis, consistency validation, and temporal reasoning.
        You have enhanced Cypher query capabilities and deep knowledge of the complete CineGraph schema.
        
        COMPLETE CINEGRAPH SCHEMA:
        {schema_json}
        
        AVAILABLE TOOLS:
        1. graph_query: Execute Cypher queries against the story knowledge graph
        2. narrative_context: Retrieve raw scene text for analysis
        3. optimized_query: Execute optimized queries using enhanced templates
        4. validate_query: Validate Cypher queries before execution
        
        ENHANCED SCHEMA CAPABILITIES:
        
        CHARACTER ENTITIES:
        - Enhanced properties: aliases, role, activity status, temporal tracking
        - Rich character analysis with first_appearance, last_mentioned
        - Activity tracking with is_active boolean
        
        KNOWLEDGE ENTITIES:
        - Knowledge types: factual, relationship, emotional, social, secret
        - Importance levels: critical, important, minor
        - Verification status: confirmed, suspected, false, unknown
        - Secret knowledge tracking with sharing restrictions
        
        SCENE ENTITIES:
        - Enhanced scene tracking with word counts and character presence
        - Timeline integration with timestamp_in_story
        - Character presence tracking with participation levels
        
        LOCATION ENTITIES:
        - Location types and accessibility levels
        - Activity tracking and usage patterns
        - Detailed environmental context
        
        ENHANCED RELATIONSHIPS:
        
        KNOWS Relationship (Character -> Knowledge):
        - learned_at: When knowledge was acquired
        - confidence_level: certain, probable, suspected, rumored
        - sharing_restrictions: can_share, must_keep_secret, conditional_sharing
        - emotional_impact: positive, negative, neutral, shocking
        - knowledge_context: Circumstances of acquisition
        
        RELATIONSHIP Relationship (Character -> Character):
        - relationship_type: family, friend, enemy, ally, romantic, professional, stranger
        - relationship_strength: 1-10 scale
        - trust_level: 1-10 scale
        - emotional_valence: love, like, neutral, dislike, hate
        - power_dynamic: equal, dominant, submissive, complex
        - temporal tracking: established_at, last_interaction
        
        PRESENT_IN Relationship (Character -> Scene):
        - arrival_time, departure_time: Scene timing
        - participation_level: active, passive, mentioned, background
        - dialogue_count: Number of dialogue lines
        - character_state: Emotional/physical state
        - actions_performed: Array of key actions
        
        OCCURS_IN Relationship (Scene -> Location):
        - Environmental context: time_of_day, weather_conditions
        - scene_duration: How long the scene lasts
        - location_accessibility: How characters accessed location
        
        CONTRADICTS Relationship (Knowledge -> Knowledge):
        - contradiction_type: factual, temporal, logical, character_behavior
        - severity: critical, major, minor, potential
        - resolution_status: unresolved, resolved, false_positive, ignored
        - detected_at: When contradiction was found
        
        IMPLIES Relationship (Knowledge -> Knowledge):
        - implication_strength: certain, probable, possible, weak
        - logical_basis: Explanation of the logical connection
        
        ENHANCED QUERY PATTERNS:
        
        1. CHARACTER ANALYSIS:
        - Character knowledge at specific times with confidence levels
        - Character activity timelines and participation patterns
        - Character relationship networks with trust analysis
        - Character aliases and role tracking
        
        2. KNOWLEDGE ANALYSIS:
        - Knowledge by type and importance level
        - Secret knowledge detection and sharing patterns
        - Knowledge propagation and implication chains
        - Verification status tracking
        
        3. TEMPORAL ANALYSIS:
        - Bi-temporal queries with valid_from/valid_to
        - Character knowledge evolution over time
        - Scene timeline with environmental context
        - Relationship changes over time
        
        4. CONSISTENCY VALIDATION:
        - Contradiction detection with severity levels
        - Temporal consistency checking
        - Character behavior consistency
        - Knowledge verification and conflict resolution
        
        5. RELATIONSHIP ANALYSIS:
        - Relationship strength and trust networks
        - Power dynamics and emotional valence
        - Mutual relationship validation
        - Relationship evolution tracking
        
        ENHANCED QUERY TEMPLATES AVAILABLE:
        - character_knowledge_at_time: Knowledge with confidence and emotional impact
        - character_relationships_detailed: Full relationship analysis
        - secret_knowledge: Secret knowledge with sharing restrictions
        - contradictions_by_severity: Prioritized contradiction detection
        - knowledge_sharing_patterns: Knowledge propagation analysis
        - character_trust_network: Trust-based relationship mapping
        - location_accessibility: Location usage and access patterns
        - scene_participation_analysis: Character participation in scenes
        
        TEMPORAL QUERY EXAMPLES:
        
        "What did character X know at time Y with confidence levels?"
        MATCH (c:Character {{name: $character_name, story_id: $story_id}})-[knows:KNOWS]->(k:Knowledge)
        WHERE k.valid_from <= $timestamp AND (k.valid_to IS NULL OR k.valid_to >= $timestamp)
        RETURN k, knows.confidence_level, knows.emotional_impact, knows.learned_at
        
        "Find all secret knowledge that must be kept secret:"
        MATCH (c:Character {{story_id: $story_id}})-[knows:KNOWS]->(k:Knowledge)
        WHERE k.is_secret = true AND knows.sharing_restrictions = 'must_keep_secret'
        RETURN c, k, knows.emotional_impact
        
        "Analyze relationship strength between characters:"
        MATCH (c1:Character {{story_id: $story_id}})-[r:RELATIONSHIP]->(c2:Character)
        WHERE r.relationship_strength >= 7 AND r.trust_level >= 8
        RETURN c1, c2, r.relationship_type, r.relationship_strength, r.trust_level
        
        VALIDATION RULES:
        - Entity validation: Unique names, required fields, proper types
        - Relationship validation: Valid connections, temporal consistency
        - Consistency rules: Timeline coherence, character behavior consistency
        - Enum validation: All enum values must match schema definitions
        
        SAFETY GUIDELINES:
        - Only use READ operations (MATCH, RETURN, WHERE, ORDER BY, LIMIT)
        - Never use destructive operations (DELETE, DROP, CREATE, MERGE, SET, REMOVE)
        - Always include proper data isolation filters (story_id, user_id)
        - Validate queries before execution using enhanced validation
        - Use enum values exactly as defined in schema
        
        ANALYSIS PRIORITIES:
        1. Critical contradictions and consistency issues
        2. Character knowledge and relationship inconsistencies
        3. Temporal logic violations
        4. Secret knowledge leakage patterns
        5. Relationship strength and trust analysis
        
        Always provide detailed explanations with:
        - Severity levels (critical, major, minor, potential)
        - Confidence levels and verification status
        - Temporal context and timeline implications
        - Relationship dynamics and trust implications
        - Actionable recommendations for resolution
        
        Use the enhanced capabilities to provide deeper insights and more accurate analysis.
        """
    
    def _build_enhanced_tool_schemas(self) -> List[Dict[str, Any]]:
        """Build enhanced OpenAI function schemas for available tools."""
        return [
            {
                "name": "graph_query",
                "description": "Execute a validated Cypher query against the story knowledge graph",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cypher_query": {
                            "type": "string",
                            "description": "The Cypher query to execute (will be validated for safety)"
                        },
                        "params": {
                            "type": "object",
                            "description": "Parameters for the query",
                            "properties": {},
                            "additionalProperties": True
                        },
                        "use_cache": {
                            "type": "boolean",
                            "description": "Whether to use query caching (default: true)",
                            "default": True
                        }
                    },
                    "required": ["cypher_query"]
                }
            },
            {
                "name": "optimized_query",
                "description": "Execute an optimized query using enhanced predefined templates",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "template_name": {
                            "type": "string",
                            "description": "Name of the enhanced query template to use",
                            "enum": [
                                "character_knowledge_at_time", "characters_in_scene", "scene_location_details",
                                "character_relationships_detailed", "knowledge_by_type", "secret_knowledge",
                                "temporal_knowledge_conflicts", "story_timeline_detailed", "knowledge_propagation",
                                "contradictions_by_severity", "character_activity_timeline", "location_accessibility",
                                "relationship_strength_analysis", "character_trust_network", "knowledge_sharing_patterns",
                                "scene_participation_analysis", "relationship_milestones_over_time", "plot_thread_resolution_status"
                            ]
                        },
                        "params": {
                            "type": "object",
                            "description": "Parameters for the template query",
                            "properties": {
                                "story_id": {"type": "string", "description": "Required story identifier"},
                                "user_id": {"type": "string", "description": "Required user identifier"},
                                "character_name": {"type": "string", "description": "Character name for character-specific queries"},
                                "scene_id": {"type": "string", "description": "Scene identifier for scene-specific queries"},
                                "timestamp": {"type": "string", "description": "Timestamp for temporal queries"},
                                "knowledge_type": {"type": "string", "enum": ["factual", "relationship", "emotional", "social", "secret"]},
                                "importance_level": {"type": "string", "enum": ["critical", "important", "minor"]},
                                "severity": {"type": "string", "enum": ["critical", "major", "minor", "potential"]},
                                "accessibility": {"type": "string", "enum": ["public", "private", "restricted", "secret"]},
                                "min_strength": {"type": "integer", "minimum": 1, "maximum": 10},
                                "min_trust_level": {"type": "integer", "minimum": 1, "maximum": 10}
                            },
                            "required": ["story_id", "user_id"],
                            "additionalProperties": True
                        }
                    },
                    "required": ["template_name", "params"]
                }
            },
            {
                "name": "validate_query",
                "description": "Validate a Cypher query for safety and correctness before execution",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cypher_query": {
                            "type": "string",
                            "description": "The Cypher query to validate"
                        }
                    },
                    "required": ["cypher_query"]
                }
            },
            {
                "name": "narrative_context",
                "description": "Retrieve raw scene text for a given story",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {
                            "type": "string",
                            "description": "The story identifier"
                        },
                        "scene_id": {
                            "type": "string",
                            "description": "Optional scene identifier for specific scene text"
                        }
                    },
                    "required": ["story_id"]
                }
            },
            {
                "name": "episode_analysis",
                "description": "Analyze episodic content structure and narrative flow across story episodes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {
                            "type": "string",
                            "description": "The story identifier"
                        },
                        "episode_range": {
                            "type": "object",
                            "description": "Range of episodes to analyze",
                            "properties": {
                                "start_episode": {"type": "integer", "minimum": 1},
                                "end_episode": {"type": "integer", "minimum": 1}
                            }
                        },
                        "analysis_type": {
                            "type": "string",
                            "enum": ["narrative_flow", "character_development", "plot_progression", "thematic_analysis", "pacing_analysis"],
                            "description": "Type of episodic analysis to perform"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User identifier for data isolation"
                        }
                    },
                    "required": ["story_id", "analysis_type", "user_id"]
                }
            },
            {
                "name": "relationship_evolution",
                "description": "Track and analyze how character relationships evolve over time and story episodes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {
                            "type": "string",
                            "description": "The story identifier"
                        },
                        "character_pairs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "character_a": {"type": "string"},
                                    "character_b": {"type": "string"}
                                },
                                "required": ["character_a", "character_b"]
                            },
                            "description": "Specific character pairs to analyze (optional - analyzes all if not provided)"
                        },
                        "time_range": {
                            "type": "object",
                            "description": "Time range for relationship evolution analysis",
                            "properties": {
                                "start_time": {"type": "string", "format": "date-time"},
                                "end_time": {"type": "string", "format": "date-time"}
                            }
                        },
                        "evolution_metrics": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["trust_level", "relationship_strength", "emotional_valence", "power_dynamic", "interaction_frequency"]
                            },
                            "description": "Specific relationship metrics to track"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User identifier for data isolation"
                        }
                    },
                    "required": ["story_id", "user_id"]
                }
            },
            {
                "name": "sna_overview",
                "description": "Perform Social Network Analysis (SNA) to provide overview of character relationship networks and social dynamics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {
                            "type": "string",
                            "description": "The story identifier"
                        },
                        "network_scope": {
                            "type": "string",
                            "enum": ["full_story", "episode_range", "character_centric"],
                            "description": "Scope of the social network analysis"
                        },
                        "scope_parameters": {
                            "type": "object",
                            "description": "Parameters specific to the chosen network scope",
                            "properties": {
                                "episodes": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Episode numbers for episode_range scope"
                                },
                                "central_character": {
                                    "type": "string",
                                    "description": "Central character for character_centric scope"
                                },
                                "degrees_of_separation": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 5,
                                    "description": "Degrees of separation for character_centric analysis"
                                }
                            }
                        },
                        "analysis_metrics": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["centrality", "clustering", "community_detection", "influence_paths", "network_density", "bridge_characters"]
                            },
                            "description": "SNA metrics to calculate"
                        },
                        "relationship_filters": {
                            "type": "object",
                            "description": "Filters for relationship types to include in analysis",
                            "properties": {
                                "relationship_types": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": ["family", "friend", "enemy", "ally", "romantic", "professional", "stranger"]
                                    }
                                },
                                "min_trust_level": {"type": "integer", "minimum": 1, "maximum": 10},
                                "min_relationship_strength": {"type": "integer", "minimum": 1, "maximum": 10}
                            }
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User identifier for data isolation"
                        }
                    },
                    "required": ["story_id", "network_scope", "user_id"]
                }
            }
        ]
    
    def _setup_redis_alerts(self):
        """Setup Redis alerts listener for processing contradiction alerts."""
        alert_manager.add_alert_handler("cinegraph_agent", self._handle_alert)
    
    def validate_schema_property(self, entity_type: str, property_name: str, value: Any) -> Tuple[bool, str]:
        """Validate a property value against the schema definition."""
        try:
            # Find the entity in schema
            entity_schema = None
            for entity in self.schema_context['entities']:
                if entity['name'] == entity_type:
                    entity_schema = entity
                    break
            
            if not entity_schema:
                return False, f"Entity type '{entity_type}' not found in schema"
            
            # Check if property exists
            if property_name not in entity_schema['properties']:
                return False, f"Property '{property_name}' not found for entity '{entity_type}'"
            
            prop_def = entity_schema['properties'][property_name]
            
            # Check required fields
            if prop_def.get('required', False) and value is None:
                return False, f"Required property '{property_name}' cannot be null"
            
            # Check type validation
            expected_type = prop_def.get('type', 'string')
            if expected_type == 'enum':
                allowed_values = prop_def.get('values', [])
                if value not in allowed_values:
                    return False, f"Value '{value}' not in allowed enum values: {allowed_values}"
            elif expected_type == 'integer':
                if not isinstance(value, int):
                    return False, f"Expected integer, got {type(value)}"
                # Check min/max constraints
                if 'min' in prop_def and value < prop_def['min']:
                    return False, f"Value {value} below minimum {prop_def['min']}"
                if 'max' in prop_def and value > prop_def['max']:
                    return False, f"Value {value} above maximum {prop_def['max']}"
            elif expected_type == 'boolean':
                if not isinstance(value, bool):
                    return False, f"Expected boolean, got {type(value)}"
            elif expected_type == 'array':
                if not isinstance(value, list):
                    return False, f"Expected array, got {type(value)}"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def validate_relationship_property(self, relationship_type: str, property_name: str, value: Any) -> Tuple[bool, str]:
        """Validate a relationship property value against the schema definition."""
        try:
            # Find the relationship in schema
            relationship_schema = None
            for relationship in self.schema_context['relationships']:
                if relationship['type'] == relationship_type:
                    relationship_schema = relationship
                    break
            
            if not relationship_schema:
                return False, f"Relationship type '{relationship_type}' not found in schema"
            
            # Check if property exists
            if property_name not in relationship_schema['properties']:
                return False, f"Property '{property_name}' not found for relationship '{relationship_type}'"
            
            prop_def = relationship_schema['properties'][property_name]
            
            # Check required fields
            if prop_def.get('required', False) and value is None:
                return False, f"Required property '{property_name}' cannot be null"
            
            # Check type validation
            expected_type = prop_def.get('type', 'string')
            if expected_type == 'enum':
                allowed_values = prop_def.get('values', [])
                if value not in allowed_values:
                    return False, f"Value '{value}' not in allowed enum values: {allowed_values}"
            elif expected_type == 'integer':
                if not isinstance(value, int):
                    return False, f"Expected integer, got {type(value)}"
                # Check min/max constraints
                if 'min' in prop_def and value < prop_def['min']:
                    return False, f"Value {value} below minimum {prop_def['min']}"
                if 'max' in prop_def and value > prop_def['max']:
                    return False, f"Value {value} above maximum {prop_def['max']}"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def validate_temporal_consistency(self, valid_from: str, valid_to: str = None) -> Tuple[bool, str]:
        """Validate temporal consistency for bi-temporal properties."""
        try:
            from datetime import datetime
            
            # Parse timestamps
            from_dt = datetime.fromisoformat(valid_from.replace('Z', '+00:00'))
            
            if valid_to:
                to_dt = datetime.fromisoformat(valid_to.replace('Z', '+00:00'))
                if from_dt > to_dt:
                    return False, f"valid_from ({valid_from}) must be <= valid_to ({valid_to})"
            
            return True, "Temporal consistency valid"
            
        except Exception as e:
            return False, f"Temporal validation error: {str(e)}"
    
    def validate_enum_value(self, enum_name: str, value: str) -> Tuple[bool, str]:
        """Validate that a value is in the allowed enum values."""
        try:
            if enum_name not in self.schema_context['enums']:
                return False, f"Enum '{enum_name}' not found in schema"
            
            allowed_values = self.schema_context['enums'][enum_name]
            if value not in allowed_values:
                return False, f"Value '{value}' not in allowed enum values: {allowed_values}"
            
            return True, "Valid enum value"
            
        except Exception as e:
            return False, f"Enum validation error: {str(e)}"
    
    def validate_query_parameters(self, query: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate query parameters against schema requirements."""
        try:
            validation_errors = []
            
            # Check required parameters
            required_params = ['story_id', 'user_id']
            for param in required_params:
                if param not in params:
                    validation_errors.append(f"Missing required parameter: {param}")
            
            # Validate enum parameters if present
            enum_params = {
                'knowledge_type': 'knowledge_type',
                'importance_level': 'importance_level',
                'severity': 'severity',
                'relationship_type': 'relationship_type',
                'emotional_valence': 'emotional_valence',
                'confidence_level': 'confidence_level'
            }
            
            for param_name, enum_name in enum_params.items():
                if param_name in params:
                    is_valid, error = self.validate_enum_value(enum_name, params[param_name])
                    if not is_valid:
                        validation_errors.append(f"Parameter '{param_name}': {error}")
            
            # Validate integer range parameters
            if 'relationship_strength' in params:
                strength = params['relationship_strength']
                if not isinstance(strength, int) or strength < 1 or strength > 10:
                    validation_errors.append("relationship_strength must be an integer between 1 and 10")
            
            if 'trust_level' in params:
                trust = params['trust_level']
                if not isinstance(trust, int) or trust < 1 or trust > 10:
                    validation_errors.append("trust_level must be an integer between 1 and 10")
            
            if validation_errors:
                return False, "; ".join(validation_errors)
            
            return True, "Parameters valid"
            
        except Exception as e:
            return False, f"Parameter validation error: {str(e)}"
    
    async def validate_cypher_query(self, cypher_query: str) -> Tuple[bool, str]:
        """Enhanced validation of Cypher queries for safety and schema compliance."""
        try:
            # Check for dangerous operations
            query_upper = cypher_query.upper()
            for dangerous_op in self.dangerous_operations:
                if dangerous_op in query_upper:
                    return False, f"Dangerous operation '{dangerous_op}' detected. Only read operations are allowed."
            
            # Check for required data isolation filters
            if 'story_id' not in query_upper and '$story_id' not in query_upper:
                return False, "Query must include story_id filter for data isolation"
            
            # Check for proper entity and relationship usage
            valid_entities = [entity['name'] for entity in self.schema_context['entities']]
            valid_relationships = [rel['type'] for rel in self.schema_context['relationships']]
            
            # Basic syntax validation
            if not self._validate_cypher_syntax(cypher_query):
                return False, "Invalid Cypher syntax detected"
            
            # Check for proper temporal query patterns
            if 'valid_from' in query_upper or 'valid_to' in query_upper:
                if not self._validate_temporal_query_pattern(cypher_query):
                    return False, "Invalid temporal query pattern. Use proper temporal constraints."
            
            # Check for enum usage in query
            enum_validation_errors = self._validate_enum_usage_in_query(cypher_query)
            if enum_validation_errors:
                return False, f"Enum validation errors: {'; '.join(enum_validation_errors)}"
            
            return True, "Query validation passed"
            
        except Exception as e:
            return False, f"Query validation error: {str(e)}"
    
    def _validate_cypher_syntax(self, query: str) -> bool:
        """Basic Cypher syntax validation."""
        try:
            # Check for balanced parentheses
            paren_count = 0
            bracket_count = 0
            brace_count = 0
            
            for char in query:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                elif char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                
                # Check for negative counts (closing before opening)
                if paren_count < 0 or bracket_count < 0 or brace_count < 0:
                    return False
            
            # Check if all are balanced
            if paren_count != 0 or bracket_count != 0 or brace_count != 0:
                return False
            
            # Check for basic Cypher structure
            query_upper = query.upper()
            if 'MATCH' not in query_upper and 'RETURN' not in query_upper:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_temporal_query_pattern(self, query: str) -> bool:
        """Validate temporal query patterns for bi-temporal support."""
        try:
            # Check for proper temporal constraints
            query_lower = query.lower()
            
            # If valid_from is used, ensure proper comparison
            if 'valid_from' in query_lower:
                # Should have proper temporal comparison
                if not any(op in query_lower for op in ['<=', '>=', '<', '>', '=']):
                    return False
            
            # If valid_to is used, ensure proper null handling
            if 'valid_to' in query_lower:
                # Should handle null values properly
                if 'is null' not in query_lower and 'is not null' not in query_lower:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_enum_usage_in_query(self, query: str) -> List[str]:
        """Validate enum values used in query against schema definitions."""
        errors = []
        
        try:
            # Extract potential enum values from query
            import re
            
            # Find string literals in query
            string_literals = re.findall(r"'([^']+)'", query)
            string_literals.extend(re.findall(r'"([^"]+)"', query))
            
            # Check against known enum values
            for enum_name, enum_values in self.schema_context['enums'].items():
                for literal in string_literals:
                    if literal in enum_values:
                        # This is a valid enum usage
                        continue
                    elif literal.lower() in [v.lower() for v in enum_values]:
                        # Case mismatch
                        errors.append(f"Enum value '{literal}' has incorrect case. Use: {enum_values}")
            
            return errors
            
        except Exception as e:
            return [f"Enum validation error: {str(e)}"]
    
    def get_query_suggestions(self, query: str) -> List[str]:
        """Get optimization suggestions for a query based on enhanced schema."""
        suggestions = []
        
        try:
            query_upper = query.upper()
            
            # Suggest using query templates
            if 'CHARACTER' in query_upper and 'KNOWS' in query_upper:
                suggestions.append("Consider using 'character_knowledge_at_time' template for character knowledge queries")
            
            if 'RELATIONSHIP' in query_upper and 'CHARACTER' in query_upper:
                suggestions.append("Consider using 'character_relationships_detailed' template for relationship analysis")
            
            if 'CONTRADICTS' in query_upper:
                suggestions.append("Consider using 'contradictions_by_severity' template for contradiction analysis")
            
            # Suggest adding filters for performance
            if 'story_id' not in query_upper:
                suggestions.append("Add story_id filter for better performance and data isolation")
            
            if 'user_id' not in query_upper:
                suggestions.append("Add user_id filter for proper data isolation")
            
            # Suggest using indexes
            if 'ORDER BY' in query_upper:
                suggestions.append("Consider adding appropriate indexes for ORDER BY clauses")
            
            # Suggest temporal optimizations
            if 'valid_from' in query.lower() or 'valid_to' in query.lower():
                suggestions.append("Use temporal indexes for better performance on temporal queries")
            
            # Suggest enum constraints
            if any(enum_name in query_upper for enum_name in self.schema_context['enums']):
                suggestions.append("Use enum constraints to improve query performance")
            
            return suggestions
            
        except Exception as e:
            return [f"Error generating suggestions: {str(e)}"]
    
    def _get_query_suggestions(self, query: str) -> List[str]:
        """Legacy method for backward compatibility."""
        return self.get_query_suggestions(query)
    
    def _generate_query_hash(self, cypher_query: str, params: dict) -> str:
        """Generate a hash for query caching."""
        query_string = f"{cypher_query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(query_string.encode()).hexdigest()
    
    async def _optimize_query(self, cypher_query: str) -> str:
        """Optimize a Cypher query for better performance."""
        # Add common optimizations
        optimized_query = cypher_query
        
        # Add index hints for common patterns
        if 'story_id' in optimized_query and 'WHERE' in optimized_query.upper():
            # Query is already likely optimized with story_id filter
            pass
        
        # Add LIMIT if not present and query might return many results
        if 'LIMIT' not in optimized_query.upper() and 'COUNT' not in optimized_query.upper():
            if any(pattern in optimized_query.upper() for pattern in ['MATCH (', 'OPTIONAL MATCH']):
                optimized_query += " LIMIT 1000"  # Safety limit
        
        return optimized_query
    
    async def _try_episodic_translation(self, cypher_query: str, params: dict) -> dict:
        """
        Attempt to translate common Cypher query patterns to episodic API calls.
        
        Args:
            cypher_query: The Cypher query to translate
            params: Query parameters
        
        Returns:
            Dict with episodic API result if translation successful, None otherwise
        """
        try:
            query_upper = cypher_query.upper()
            story_id = params.get('story_id')
            
            # Pattern 1: Count queries -> use get_query_statistics
            if 'COUNT(' in query_upper and 'RETURN' in query_upper:
                stats = await self.graphiti_manager.get_query_statistics()
                return {
                    "success": True,
                    "data": [stats],
                    "translated_from": "cypher_count",
                    "api_used": "get_query_statistics",
                    "note": "Translated COUNT query to episodic statistics API"
                }
            
            # Pattern 2: Content search -> use search API
            if 'CONTAINS' in query_upper or 'LIKE' in query_upper:
                if story_id:
                    session_id = self.graphiti_manager._story_sessions.get(story_id)
                    if session_id:
                        # Extract search term from query
                        search_term = self._extract_search_term(cypher_query)
                        if search_term:
                            search_results = await self.graphiti_manager.client.search(
                                query=search_term,
                                group_ids=[session_id],
                                num_results=50
                            )
                            return {
                                "success": True,
                                "data": search_results,
                                "translated_from": "cypher_content_search",
                                "api_used": "search",
                                "search_term": search_term,
                                "note": "Translated content search query to episodic search API"
                            }
            
            # Pattern 3: Temporal queries -> use retrieve_episodes
            if 'CREATED_AT' in query_upper or 'VALID_FROM' in query_upper or 'ORDER BY' in query_upper:
                if story_id:
                    session_id = self.graphiti_manager._story_sessions.get(story_id)
                    if session_id:
                        episodes = await self.graphiti_manager.client.retrieve_episodes(
                            reference_time=datetime.utcnow(),
                            last_n=20,
                            group_ids=[session_id]
                        )
                        return {
                            "success": True,
                            "data": episodes,
                            "translated_from": "cypher_temporal",
                            "api_used": "retrieve_episodes",
                            "note": "Translated temporal query to episodic retrieve_episodes API"
                        }
            
            # No translation possible
            return None
            
        except Exception as e:
            print(f"Error in episodic translation: {str(e)}")
            return None
    
    def _extract_search_term(self, cypher_query: str) -> str:
        """
        Extract search term from Cypher query containing CONTAINS or LIKE.
        
        Args:
            cypher_query: The Cypher query
        
        Returns:
            Extracted search term or '*' as fallback
        """
        try:
            import re
            
            # Look for CONTAINS 'term' or LIKE '%term%'
            contains_match = re.search(r"CONTAINS\s+['\"]([^'\"]+)['\"]|LIKE\s+['\"]%?([^'\"]+)%?['\"]]", cypher_query, re.IGNORECASE)
            if contains_match:
                return contains_match.group(1) or contains_match.group(2)
            
            # Fallback to wildcard search
            return '*'
            
        except Exception:
            return '*'
    
    async def graph_query(self, cypher_query: str, params: dict = None, use_cache: bool = True) -> dict:
        """
        DEPRECATED: Direct Cypher queries are being phased out in favor of episodic APIs.
        
        This method now attempts to translate common query patterns to episodic API calls
        where possible, falling back to controlled Cypher execution for backwards compatibility.
        
        For new code, use:
        - graphiti_manager.client.search() for content queries
        - graphiti_manager.client.retrieve_episodes() for temporal queries
        - graphiti_manager.get_query_statistics() for statistics
        """
        try:
            if params is None:
                params = {}
            
            # Attempt to translate common query patterns to episodic APIs
            episodic_result = await self._try_episodic_translation(cypher_query, params)
            if episodic_result:
                return episodic_result
            
            # Validate the query first (legacy path)
            is_valid, validation_message = await self.validate_cypher_query(cypher_query)
            if not is_valid:
                return {
                    "success": False, 
                    "error": f"Query validation failed: {validation_message}",
                    "suggestion": "Consider using episodic APIs: search() or retrieve_episodes()"
                }
            
            # Check cache if enabled
            if use_cache:
                query_hash = self._generate_query_hash(cypher_query, params)
                if query_hash in self.query_cache:
                    return {"success": True, "data": self.query_cache[query_hash], "cached": True}
            
            # Log deprecation warning
            print(f"WARNING: Direct Cypher query used. Consider migrating to episodic APIs. Query: {cypher_query[:100]}...")
            
            # Use controlled Cypher execution via GraphitiManager
            try:
                result = await self.graphiti_manager._run_cypher_query(cypher_query)
                
                # Cache the result if enabled
                if use_cache:
                    query_hash = self._generate_query_hash(cypher_query, params)
                    self.query_cache[query_hash] = result
                    # Limit cache size to prevent memory issues
                    if len(self.query_cache) > 100:
                        # Remove oldest entries
                        oldest_keys = list(self.query_cache.keys())[:20]
                        for key in oldest_keys:
                            del self.query_cache[key]
                
                return {
                    "success": True, 
                    "data": result, 
                    "cached": False,
                    "warning": "Direct Cypher is deprecated. Migrate to episodic APIs."
                }
                
            except Exception as cypher_error:
                return {
                    "success": False, 
                    "error": f"Cypher execution failed: {str(cypher_error)}",
                    "suggestion": "Consider using episodic APIs instead of direct Cypher"
                }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def optimized_query(self, template_name: str, params: dict) -> dict:
        """Execute an optimized query using predefined templates."""
        try:
            if template_name not in self.query_templates:
                return {"success": False, "error": f"Unknown template: {template_name}"}
            
            template_query = self.query_templates[template_name]
            
            # Execute using the template
            result = await self.graph_query(template_query, params, use_cache=True)
            
            return {
                "success": result["success"],
                "data": result.get("data"),
                "template_used": template_name,
                "cached": result.get("cached", False),
                "error": result.get("error")
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def validate_query(self, cypher_query: str) -> dict:
        """Validate a Cypher query and return validation results."""
        is_valid, message = await self.validate_cypher_query(cypher_query)
        
        return {
            "valid": is_valid,
            "message": message,
            "suggested_optimizations": self._get_query_suggestions(cypher_query) if is_valid else []
        }
    
    
    async def narrative_context(self, story_id: str, scene_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """Return raw scene text for a given story ID using episodic APIs."""
        try:
            # Get session for this story
            session_id = self.graphiti_manager._story_sessions.get(story_id)
            if not session_id:
                return f"No active session found for story {story_id}. Consider adding content first."
            
            if scene_id:
                # Search for specific scene using episodic API
                search_results = await self.graphiti_manager.client.search(
                    query=f"scene {scene_id}",
                    group_ids=[session_id],
                    num_results=10
                )
                
                if search_results:
                    # Extract content from search results
                    scene_content = []
                    for result in search_results:
                        content = getattr(result, 'episode_body', getattr(result, 'fact', ''))
                        if content and scene_id.lower() in content.lower():
                            scene_content.append(content)
                    
                    return "\n\n".join(scene_content) if scene_content else f"No content found for scene {scene_id}"
                else:
                    return f"No content found for scene {scene_id}"
            else:
                # Retrieve all episodes for the story using episodic API
                episodes = await self.graphiti_manager.client.retrieve_episodes(
                    reference_time=datetime.utcnow(),
                    last_n=100,  # Get more episodes for complete narrative context
                    group_ids=[session_id]
                )
                
                if episodes:
                    # Sort episodes by creation time for narrative order
                    sorted_episodes = sorted(
                        episodes, 
                        key=lambda ep: getattr(ep, 'created_at', datetime.min)
                    )
                    
                    # Extract content from episodes
                    narrative_content = []
                    for episode in sorted_episodes:
                        content = getattr(episode, 'episode_body', '')
                        if content and 'Story Content:' in content:
                            # Extract just the story content part
                            if 'Story Content:' in content:
                                story_part = content.split('Story Content:')[1].split('\n\nEntities:')[0].strip()
                                if story_part:
                                    narrative_content.append(story_part)
                            else:
                                narrative_content.append(content)
                    
                    return "\n\n".join(narrative_content) if narrative_content else f"No narrative content found for story {story_id}"
                else:
                    return f"No episodes found for story {story_id}"
                
        except Exception as e:
            return f"Error retrieving narrative context via episodic APIs: {str(e)}"
    
    async def initialize(self) -> None:
        """Initialize the CineGraph Agent."""
        # Start Redis alerts listener
        await alert_manager.start_listening()
        print("CineGraph Agent initialized and listening for alerts.")
    
    async def discover_relationships(self, movie_id: str, user_id: str) -> Dict[str, Any]:
        """
        Discover relationships from script/metadata and return Cypher ready for GraphitiManager.
        Uses SNA features and modular extractors.

        Args:
            movie_id: Unique identifier for the movie script.
            user_id: User ID for data isolation.

        Returns:
            Dict containing relationships and Cypher queries.
        """
        try:
            # Use GraphitiManager to search for existing content related to this movie
            session_id = self.graphiti_manager._story_sessions.get(movie_id)
            if not session_id:
                return {
                    "status": "error",
                    "error": f"No session found for movie {movie_id}",
                    "relationships": [],
                    "cypher_queries": []
                }
            
            # Search for dialogue and interaction data using GraphitiManager
            search_results = await self.graphiti_manager.client.search(
                query=f"dialogue interaction character {movie_id}",
                group_ids=[session_id],
                num_results=50
            )
            
            # Extract dialogue patterns from search results
            dialogue_extractor = DialoguePatternExtractor(search_results)
            dialogue_patterns = dialogue_extractor.extract_patterns()
            
            # Extract interaction strengths
            interaction_extractor = InteractionStrengthExtractor(dialogue_patterns)
            relationship_strengths = interaction_extractor.calculate_strengths()
            
            # Generate SNA-ready relationships
            sna_extractor = SNARelationshipExtractor(relationship_strengths)
            sna_relationships = sna_extractor.generate_sna_relationships()
            
            # Build Cypher queries for GraphitiManager
            cypher_queries = []
            for rel in sna_relationships:
                cypher_query = self._build_relationship_cypher(rel, movie_id, user_id)
                cypher_queries.append(cypher_query)
            
            return {
                "status": "success",
                "movie_id": movie_id,
                "relationships_discovered": len(sna_relationships),
                "relationships": sna_relationships,
                "cypher_queries": cypher_queries,
                "sna_metrics": {
                    "total_interactions": len(dialogue_patterns),
                    "unique_character_pairs": len(relationship_strengths),
                    "avg_interaction_strength": sum(rel["strength"] for rel in sna_relationships) / len(sna_relationships) if sna_relationships else 0
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "movie_id": movie_id,
                "relationships": [],
                "cypher_queries": []
            }
    
    def _build_relationship_cypher(self, relationship: Dict[str, Any], movie_id: str, user_id: str) -> str:
        """
        Build Cypher query for a single relationship.
        
        Args:
            relationship: Relationship data dict
            movie_id: Movie identifier
            user_id: User identifier
            
        Returns:
            Cypher query string
        """
        rel_type = relationship.get("type", "FRIENDS_WITH")
        from_char = relationship.get("from_character")
        to_char = relationship.get("to_character")
        strength = relationship.get("strength", 1)
        confidence = relationship.get("confidence", 0.5)
        
        cypher = f"""
        MERGE (a:Character {{name: '{from_char}', story_id: '{movie_id}', user_id: '{user_id}'}})
        MERGE (b:Character {{name: '{to_char}', story_id: '{movie_id}', user_id: '{user_id}'}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r.strength = {strength},
            r.confidence_level = {confidence},
            r.discovered_method = 'sna_extraction',
            r.story_id = '{movie_id}',
            r.user_id = '{user_id}',
            r.created_at = timestamp(),
            r.updated_at = timestamp()
        RETURN a, r, b
        """.strip()
        
        return cypher


    async def analyze_scenes(self, scenes: List[Dict[str, Any]], story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Analyze scenes using AI to extract enhanced metadata and relationships.
        
        Args:
            scenes: List of scene dictionaries
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing enhanced scene data with AI-powered analysis
        """
        try:
            if not self.openai_client:
                # Fallback to basic processing
                return await self._fallback_scene_analysis(scenes, story_id, user_id)
            
            enhanced_scenes = []
            all_entities = []
            all_relationships = []
            all_knowledge_items = []
            continuity_edges = []
            
            # Process scenes in batches for efficiency
            batch_size = 3
            for i in range(0, len(scenes), batch_size):
                batch = scenes[i:i + batch_size]
                batch_results = await self._process_scene_batch(batch, story_id, user_id)
                
                enhanced_scenes.extend(batch_results.get("scenes", []))
                all_entities.extend(batch_results.get("entities", []))
                all_relationships.extend(batch_results.get("relationships", []))
                all_knowledge_items.extend(batch_results.get("knowledge_items", []))
                continuity_edges.extend(batch_results.get("continuity_edges", []))
            
            return {
                "entities": all_entities,
                "relationships": all_relationships,
                "scenes": enhanced_scenes,
                "knowledge_items": all_knowledge_items,
                "continuity_edges": continuity_edges,
                "processing_method": "ai_enhanced",
                "model_used": self.model
            }
            
        except Exception as e:
            print(f"Warning: AI scene analysis failed: {e}")
            return await self._fallback_scene_analysis(scenes, story_id, user_id)
    
    async def _process_scene_batch(self, scenes: List[Dict[str, Any]], story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Process a batch of scenes using OpenAI for enhanced analysis.
        
        Args:
            scenes: Batch of scenes to process
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing processed batch results
        """
        scene_texts = [scene["text"] for scene in scenes]
        combined_text = "\n\n".join(scene_texts)
        
        analysis_prompt = f"""
        Analyze the following story scenes and provide structured analysis:
        
        Story ID: {story_id}
        Scenes:
        {combined_text}
        
        For each scene, provide:
        1. Chapter/Episode structure detection
        2. Point of view analysis (first/second/third person)
        3. Mood and emotional tone (happy, sad, tense, dramatic, mysterious, action)
        4. Story arc classification (exposition, rising_action, climax, falling_action, resolution)
        5. Significance score (0.0-1.0)
        6. Characters mentioned
        7. Locations mentioned
        8. Key themes or topics
        9. Continuity references (callbacks, foreshadowing)
        
        Return the analysis as a JSON object with the following structure:
        {{
            "scenes": [
                {{
                    "scene_id": "scene_1",
                    "chapter": 1,
                    "episode": 1,
                    "pov": {{"type": "first_person", "confidence": 0.9}},
                    "mood": {{"primary_mood": "tense", "intensity": 0.7, "secondary_moods": ["mysterious"]}},
                    "story_arc": {{"primary_arc": "rising_action", "intensity": 0.8}},
                    "significance": {{"score": 0.75, "reasoning": "Key plot development"}},
                    "characters": ["character_name1", "character_name2"],
                    "locations": ["location_name1"],
                    "themes": ["mystery", "fear"],
                    "continuity_references": ["reference to earlier event"]
                }}
            ],
            "entities": [...],
            "relationships": [...],
            "continuity_edges": [...]
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert story analyst. Analyze narrative structure, characters, and themes with precision."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            # Parse the JSON response
            analysis_result = json.loads(response.choices[0].message.content)
            
            # Enhance scenes with original metadata
            enhanced_scenes = []
            for i, scene in enumerate(scenes):
                if i < len(analysis_result.get("scenes", [])):
                    ai_analysis = analysis_result["scenes"][i]
                    enhanced_scene = {
                        **scene,  # Keep original metadata
                        "ai_analysis": ai_analysis,
                        "chapter": ai_analysis.get("chapter", 1),
                        "episode": ai_analysis.get("episode", 1),
                        "pov": ai_analysis.get("pov", {"type": "unknown", "confidence": 0.0}),
                        "mood": ai_analysis.get("mood", {"primary_mood": "neutral", "intensity": 0.5}),
                        "story_arc": ai_analysis.get("story_arc", {"primary_arc": "neutral", "intensity": 0.0}),
                        "significance": ai_analysis.get("significance", {"score": 0.5})
                    }
                    enhanced_scenes.append(enhanced_scene)
                else:
                    enhanced_scenes.append(scene)
            
            return {
                "scenes": enhanced_scenes,
                "entities": analysis_result.get("entities", []),
                "relationships": analysis_result.get("relationships", []),
                "knowledge_items": analysis_result.get("knowledge_items", []),
                "continuity_edges": analysis_result.get("continuity_edges", [])
            }
            
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse AI response as JSON: {e}")
            return await self._fallback_scene_analysis(scenes, story_id, user_id)
        except Exception as e:
            print(f"Warning: AI batch processing failed: {e}")
            return await self._fallback_scene_analysis(scenes, story_id, user_id)
    
    async def _fallback_scene_analysis(self, scenes: List[Dict[str, Any]], story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Fallback scene analysis using basic heuristics.
        
        Args:
            scenes: List of scene dictionaries
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing basic analysis results
        """
        # Simple fallback processing
        enhanced_scenes = []
        for i, scene in enumerate(scenes):
            enhanced_scene = {
                **scene,
                "chapter": 1,  # Default chapter
                "episode": i + 1,  # Sequential episodes
                "pov": {"type": "unknown", "confidence": 0.0},
                "mood": {"primary_mood": "neutral", "intensity": 0.5},
                "story_arc": {"primary_arc": "neutral", "intensity": 0.0},
                "significance": {"score": 0.5}
            }
            enhanced_scenes.append(enhanced_scene)
        
        return {
            "entities": [],
            "relationships": [],
            "scenes": enhanced_scenes,
            "knowledge_items": [],
            "continuity_edges": [],
            "processing_method": "fallback"
        }
    
    async def analyze_story(self, content: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze story content and provide insights using OpenAI SDK.
        
        Args:
            content: Raw story content
            extracted_data: Processed story data with entities and relationships
            
        Returns:
            Dict containing analysis insights
        """
        try:
            story_id = extracted_data.get("story_id", "unknown")
            
            # Return basic analysis if OpenAI client is not configured
            if not self.openai_client:
                return {
                    "analysis": "OpenAI client not configured. Basic analysis:",
                    "entity_count": len(extracted_data.get("entities", [])),
                    "relationship_count": len(extracted_data.get("relationships", [])),
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_analysis"
                }
            
            # Build prompt for story analysis
            analysis_prompt = f"""
            Analyze the following story content and provide insights:
            
            Story Content: {content}
            
            Extracted Data: {json.dumps(extracted_data, indent=2)}
            
            Please provide:
            1. Main themes and genres
            2. Character analysis and roles
            3. Story complexity score (0-1)
            4. Temporal structure analysis
            5. Potential inconsistencies or plot holes
            
            Use the available tools to query the knowledge graph for additional context.
            """
            
            # Call OpenAI with function calling
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                functions=self.tool_schemas,
                function_call="auto"
            )
            
            # Process function calls if any
            if response.choices[0].message.function_call:
                function_result = await self._execute_function_call(
                    response.choices[0].message.function_call,
                    story_id
                )
                
                # Continue conversation with function result
                follow_up_response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": analysis_prompt},
                        {"role": "assistant", "content": response.choices[0].message.content, "function_call": response.choices[0].message.function_call.model_dump()},
                        {"role": "function", "name": response.choices[0].message.function_call.name, "content": json.dumps(function_result)}
                    ]
                )
                analysis_result = follow_up_response.choices[0].message.content
            else:
                analysis_result = response.choices[0].message.content
            
            # Parse and structure the analysis result
            return {
                "analysis": analysis_result,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "story_id": extracted_data.get("story_id", "unknown"),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def detect_inconsistencies(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Detect inconsistencies in the story using OpenAI SDK.
        
        Args:
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing detected inconsistencies
        """
        try:
            # Return basic inconsistency detection if OpenAI client is not configured
            if not self.openai_client:
                return {
                    "inconsistencies": "OpenAI client not configured. Basic inconsistency detection not available.",
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_detection"
                }
            
            # Build prompt for inconsistency detection
            detection_prompt = f"""
            Analyze the story with ID '{story_id}' for inconsistencies.
            
            Please perform the following consistency checks:
            1. Temporal consistency - Check for events out of chronological order
            2. Character knowledge consistency - Verify characters don't know things they shouldn't
            3. Location consistency - Ensure characters aren't in multiple places simultaneously
            4. Relationship consistency - Check for conflicting character relationships
            5. Event sequence consistency - Verify cause-and-effect relationships
            
            Use the graph_query tool to examine the story's knowledge graph and narrative_context to get scene details.
            
            Return a detailed report of any inconsistencies found with:
            - Type of inconsistency
            - Severity level (low, medium, high, critical)
            - Specific examples
            - Suggested fixes
            """
            
            # Call OpenAI with function calling
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": detection_prompt}
                ],
                functions=self.tool_schemas,
                function_call="auto"
            )
            
            # Process function calls
            final_response = await self._process_function_calls(response, story_id)
            
            return {
                "inconsistencies": final_response,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def query_story(self, story_id: str, question: str, user_id: str) -> Dict[str, Any]:
        """
        Query the story using a natural language question with OpenAI SDK.
        
        Args:
            story_id: Story identifier
            question: Natural language question
            user_id: User ID for data isolation
            
        Returns:
            Dict containing query response
        """
        try:
            # Return basic query response if OpenAI client is not configured
            if not self.openai_client:
                return {
                    "answer": "OpenAI client not configured. Basic query processing not available.",
                    "question": question,
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_query"
                }
            
            # Build prompt for story querying
            query_prompt = f"""
            Answer the following question about the story with ID '{story_id}':
            
            Question: {question}
            
            Use the available tools to:
            1. Query the knowledge graph for relevant information
            2. Retrieve narrative context for detailed analysis
            3. Consider temporal aspects if the question involves "when" or "what did X know at Y"
            
            Provide a comprehensive answer with:
            - Direct answer to the question
            - Supporting evidence from the story
            - Confidence level (0-1)
            - Relevant quotes or references
            """
            
            # Call OpenAI with function calling
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": query_prompt}
                ],
                functions=self.tool_schemas,
                function_call="auto"
            )
            
            # Process function calls
            final_response = await self._process_function_calls(response, story_id)
            
            return {
                "answer": final_response,
                "question": question,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "question": question,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def validate_story_consistency(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """
        Validate the consistency of the entire story using OpenAI SDK.
        
        Args:
            story_id: Story identifier
            user_id: User ID for data isolation
            
        Returns:
            Dict containing validation report
        """
        try:
            # Return basic validation if OpenAI client is not configured
            if not self.openai_client:
                return {
                    "validation_report": "OpenAI client not configured. Basic validation not available.",
                    "story_id": story_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_used": "basic_validation"
                }
            
            # Build prompt for comprehensive story validation
            validation_prompt = f"""
            Perform a comprehensive consistency validation of the story with ID '{story_id}'.
            
            Please analyze:
            1. Overall story coherence and logical flow
            2. Character consistency throughout the narrative
            3. Timeline and temporal consistency
            4. Plot coherence and cause-effect relationships
            5. Setting and world-building consistency
            6. Dialogue and character voice consistency
            
            Use the available tools to:
            - Query the knowledge graph for character relationships and events
            - Retrieve narrative context for detailed scene analysis
            - Perform temporal queries to check chronological consistency
            
            Provide a comprehensive validation report with:
            - Overall consistency score (0-1)
            - Summary of findings
            - Detailed breakdown by category
            - Specific issues found with severity levels
            - Recommendations for improvement
            """
            
            # Call OpenAI with function calling
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": validation_prompt}
                ],
                functions=self.tool_schemas,
                function_call="auto"
            )
            
            # Process function calls
            final_response = await self._process_function_calls(response, story_id)
            
            return {
                "validation_report": final_response,
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": self.model
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "story_id": story_id,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the CineGraph Agent using episodic APIs."""
        try:
            # Test OpenAI connection
            test_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )
            
            # Test Supabase connection
            supabase_health = self.supabase.table("alerts").select("count").execute()
            
            # Test GraphitiManager connection using episodic APIs
            graphiti_health = await self.graphiti_manager.health_check()
            
            # Additional test: try to retrieve episodes to confirm episodic API connectivity
            episodic_connectivity = False
            try:
                # Test episodic API with minimal query
                episodes_result = await self.graphiti_manager.client.retrieve_episodes(
                    reference_time=datetime.utcnow(),
                    last_n=1,
                    group_ids=None
                ) if self.graphiti_manager.client else None
                episodic_connectivity = episodes_result is not None
            except Exception:
                episodic_connectivity = False
            
            return {
                "status": "healthy",
                "components": {
                    "openai": "connected",
                    "supabase": "connected",
                    "graphiti": graphiti_health["status"],
                    "episodic_api": "connected" if episodic_connectivity else "degraded",
                    "redis_alerts": "listening" if alert_manager.is_listening else "not_listening"
                },
                "graphiti_details": graphiti_health,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Health check using episodic APIs"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_function_call(self, function_call, story_id: str) -> Any:
        """Execute a function call from OpenAI with enhanced tool support."""
        function_name = function_call.name
        function_args = json.loads(function_call.arguments)
        
        if function_name == "graph_query":
            return await self.graph_query(
                function_args.get("cypher_query"),
                function_args.get("params", {}),
                function_args.get("use_cache", True)
            )
        elif function_name == "optimized_query":
            return await self.optimized_query(
                function_args.get("template_name"),
                function_args.get("params", {})
            )
        elif function_name == "validate_query":
            return await self.validate_query(
                function_args.get("cypher_query")
            )
        elif function_name == "narrative_context":
            return await self.narrative_context(
                function_args.get("story_id", story_id),
                function_args.get("scene_id")
            )
        elif function_name == "episode_analysis":
            return await self.episode_analysis(
                function_args.get("story_id", story_id),
                function_args.get("analysis_type"),
                function_args.get("user_id"),
                function_args.get("episode_range")
            )
        elif function_name == "relationship_evolution":
            return await self.relationship_evolution(
                function_args.get("story_id", story_id),
                function_args.get("user_id"),
                function_args.get("character_pairs"),
                function_args.get("time_range"),
                function_args.get("evolution_metrics")
            )
        elif function_name == "sna_overview":
            return await self.sna_overview(
                function_args.get("story_id", story_id),
                function_args.get("user_id"),
                function_args.get("network_scope"),
                function_args.get("scope_parameters"),
                function_args.get("analysis_metrics"),
                function_args.get("relationship_filters")
            )
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    async def _process_function_calls(self, response, story_id: str) -> str:
        """Process function calls in OpenAI response."""
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        current_response = response
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        while (current_response.choices[0].message.function_call and 
               iteration < max_iterations):
            
            function_call = current_response.choices[0].message.function_call
            function_result = await self._execute_function_call(function_call, story_id)
            
            # Add messages to conversation
            messages.append({
                "role": "assistant",
                "content": current_response.choices[0].message.content,
                "function_call": function_call.model_dump()
            })
            messages.append({
                "role": "function",
                "name": function_call.name,
                "content": json.dumps(function_result)
            })
            
            # Continue conversation
            current_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=self.tool_schemas,
                function_call="auto"
            )
            
            iteration += 1
        
        return current_response.choices[0].message.content
    
    async def _handle_alert(self, alert_data: Dict[str, Any]):
        """Handle incoming Redis alert by enriching and storing in Supabase."""
        try:
            # Enrich alert with explanation using OpenAI
            enrichment_prompt = f"""
            Analyze this contradiction alert and provide:
            1. Detailed explanation of the inconsistency
            2. Severity assessment (low, medium, high, critical)
            3. Potential impact on story coherence
            4. Suggested resolution steps
            
            Alert Data: {json.dumps(alert_data, indent=2)}
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": enrichment_prompt}
                ],
                max_tokens=500
            )
            
            explanation = response.choices[0].message.content
            
            # Determine severity based on alert data
            severity = self._assess_alert_severity(alert_data)
            
            # Create enriched alert for Supabase
            enriched_alert = {
                "id": alert_data.get("id", f"alert_{datetime.utcnow().isoformat()}"),
                "story_id": alert_data.get("story_id"),
                "alert_type": alert_data.get("alert_type", "contradiction_detected"),
                "severity": severity,
                "explanation": explanation,
                "original_alert": alert_data,
                "detected_at": alert_data.get("timestamp", datetime.utcnow().isoformat()),
                "enriched_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            # Store in Supabase realtime table
            result = self.supabase.table("alerts").insert(enriched_alert).execute()
            
            print(f"Alert enriched and stored: {enriched_alert['id']}")
            
        except Exception as e:
            print(f"Error handling alert: {str(e)}")
    
    def _assess_alert_severity(self, alert_data: Dict[str, Any]) -> str:
        """Assess the severity of an alert based on its data."""
        # Basic severity assessment logic
        reason = alert_data.get("reason", "").lower()
        
        if any(keyword in reason for keyword in ["critical", "major", "severe"]):
            return "critical"
        elif any(keyword in reason for keyword in ["significant", "important", "conflict"]):
            return "high"
        elif any(keyword in reason for keyword in ["minor", "inconsistent", "unclear"]):
            return "medium"
        else:
            return "low"
    
    # === ADVANCED ANALYSIS METHODS ===
    
    async def analyze_story_timeline(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """Analyze the story timeline for temporal consistency and flow."""
        try:
            # Use optimized query for timeline analysis
            timeline_result = await self.optimized_query(
                "story_timeline",
                {"story_id": story_id, "user_id": user_id}
            )
            
            if not timeline_result["success"]:
                return {"error": timeline_result["error"]}
            
            # Analyze temporal knowledge conflicts
            conflicts_result = await self.optimized_query(
                "temporal_knowledge_conflicts",
                {"story_id": story_id, "user_id": user_id}
            )
            
            timeline_data = timeline_result["data"]
            conflicts_data = conflicts_result.get("data", [])
            
            # Generate comprehensive analysis
            analysis = {
                "story_id": story_id,
                "total_scenes": len(timeline_data),
                "temporal_conflicts": len(conflicts_data),
                "scenes": timeline_data,
                "conflicts": conflicts_data,
                "timeline_coherence": "good" if len(conflicts_data) == 0 else "needs_attention",
                "recommendations": self._generate_timeline_recommendations(timeline_data, conflicts_data)
            }
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    async def analyze_character_consistency(self, story_id: str, character_name: str, user_id: str) -> Dict[str, Any]:
        """Analyze character consistency across the story."""
        try:
            # Get character relationships
            relationships_result = await self.optimized_query(
                "character_relationships",
                {"story_id": story_id, "character_name": character_name, "user_id": user_id}
            )
            
            # Get character knowledge evolution
            knowledge_query = """
                MATCH (c:Character {name: $character_name, story_id: $story_id})-[:KNOWS]->(k:Knowledge)
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                RETURN k
                ORDER BY k.valid_from ASC
            """
            
            knowledge_result = await self.graph_query(
                knowledge_query,
                {"story_id": story_id, "character_name": character_name, "user_id": user_id}
            )
            
            # Check for knowledge contradictions
            contradictions_query = """
                MATCH (c:Character {name: $character_name, story_id: $story_id})-[:KNOWS]->(k1:Knowledge)
                MATCH (c)-[:KNOWS]->(k2:Knowledge)
                WHERE k1.knowledge_id <> k2.knowledge_id
                AND EXISTS((k1)-[:CONTRADICTS]->(k2))
                RETURN k1, k2
            """
            
            contradictions_result = await self.graph_query(
                contradictions_query,
                {"story_id": story_id, "character_name": character_name, "user_id": user_id}
            )
            
            # Compile analysis
            return {
                "character_name": character_name,
                "story_id": story_id,
                "relationships": relationships_result.get("data", []),
                "knowledge_evolution": knowledge_result.get("data", []),
                "contradictions": contradictions_result.get("data", []),
                "consistency_score": self._calculate_character_consistency_score(
                    relationships_result.get("data", []),
                    knowledge_result.get("data", []),
                    contradictions_result.get("data", [])
                ),
                "recommendations": self._generate_character_recommendations(
                    character_name,
                    contradictions_result.get("data", [])
                )
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def detect_plot_holes(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """Detect potential plot holes using advanced graph analysis."""
        try:
            # Use custom query to find logical inconsistencies
            plot_hole_query = """
                MATCH (c:Character {story_id: $story_id})-[:KNOWS]->(k:Knowledge)
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                AND NOT EXISTS {
                    MATCH (c)-[:PRESENT_IN]->(s:Scene)
                    WHERE s.created_at <= k.valid_from
                }
                RETURN c.name as character, k.content as knowledge, 
                       'impossible_knowledge' as issue_type,
                       'Character knows something without being present when it happened' as description
                
                UNION
                
                MATCH (c:Character {story_id: $story_id})-[:PRESENT_IN]->(s1:Scene)-[:OCCURS_IN]->(l1:Location)
                MATCH (c)-[:PRESENT_IN]->(s2:Scene)-[:OCCURS_IN]->(l2:Location)
                WHERE s1.scene_order = s2.scene_order AND l1.location_id <> l2.location_id
                RETURN c.name as character, l1.name as location1, l2.name as location2,
                       'location_contradiction' as issue_type,
                       'Character cannot be in two places at once' as description
            """
            
            plot_holes_result = await self.graph_query(
                plot_hole_query,
                {"story_id": story_id, "user_id": user_id}
            )
            
            plot_holes = plot_holes_result.get("data", [])
            
            # Categorize plot holes by severity
            categorized_holes = self._categorize_plot_holes(plot_holes)
            
            return {
                "story_id": story_id,
                "total_plot_holes": len(plot_holes),
                "plot_holes_by_severity": categorized_holes,
                "detailed_analysis": plot_holes,
                "overall_coherence_score": self._calculate_coherence_score(plot_holes),
                "recommendations": self._generate_plot_hole_recommendations(plot_holes)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    # === HELPER METHODS FOR ANALYSIS ===
    
    def _generate_timeline_recommendations(self, timeline_data: List[Dict], conflicts_data: List[Dict]) -> List[str]:
        """Generate recommendations for timeline improvements."""
        recommendations = []
        
        if len(conflicts_data) > 0:
            recommendations.append(f"Resolve {len(conflicts_data)} temporal conflicts in the story")
        
        if len(timeline_data) > 50:
            recommendations.append("Consider breaking the story into chapters for better organization")
        
        return recommendations
    
    def _calculate_character_consistency_score(self, relationships: List, knowledge: List, contradictions: List) -> float:
        """Calculate a consistency score for a character."""
        base_score = 1.0
        
        # Deduct for contradictions
        contradiction_penalty = len(contradictions) * 0.1
        
        # Bonus for rich character development
        development_bonus = min(len(knowledge) * 0.02, 0.2)
        
        score = max(0.0, base_score - contradiction_penalty + development_bonus)
        return min(1.0, score)
    
    def _generate_character_recommendations(self, character_name: str, contradictions: List) -> List[str]:
        """Generate recommendations for character consistency."""
        recommendations = []
        
        if len(contradictions) > 0:
            recommendations.append(f"Resolve {len(contradictions)} knowledge contradictions for {character_name}")
        
        return recommendations
    
    def _categorize_plot_holes(self, plot_holes: List) -> Dict[str, List]:
        """Categorize plot holes by severity."""
        categories = {"critical": [], "major": [], "minor": []}
        
        for hole in plot_holes:
            issue_type = hole.get("issue_type", "unknown")
            if issue_type == "temporal_paradox":
                categories["critical"].append(hole)
            elif issue_type == "location_contradiction":
                categories["major"].append(hole)
            else:
                categories["minor"].append(hole)
        
        return categories
    
    def _calculate_coherence_score(self, plot_holes: List) -> float:
        """Calculate overall story coherence score."""
        if not plot_holes:
            return 1.0
        
        # Simple scoring based on number and severity of plot holes
        critical_holes = sum(1 for hole in plot_holes if hole.get("issue_type") == "temporal_paradox")
        major_holes = sum(1 for hole in plot_holes if hole.get("issue_type") == "location_contradiction")
        minor_holes = len(plot_holes) - critical_holes - major_holes
        
        penalty = (critical_holes * 0.3) + (major_holes * 0.2) + (minor_holes * 0.1)
        return max(0.0, 1.0 - penalty)
    
    def _generate_plot_hole_recommendations(self, plot_holes: List) -> List[str]:
        """Generate recommendations for fixing plot holes."""
        recommendations = []
        
        categorized = self._categorize_plot_holes(plot_holes)
        
        if categorized["critical"]:
            recommendations.append(f"Address {len(categorized['critical'])} critical plot holes immediately")
        
        if categorized["major"]:
            recommendations.append(f"Review {len(categorized['major'])} major inconsistencies")
        
        if categorized["minor"]:
            recommendations.append(f"Consider resolving {len(categorized['minor'])} minor issues")
        
        return recommendations
    
    # === NEW TIER-2 AGENT TOOLS ===
    
    async def episode_analysis(self, story_id: str, analysis_type: str, user_id: str, episode_range: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Analyze episodic content structure and narrative flow across story episodes."""
        try:
            if not self.graphiti_manager:
                return {"error": "GraphitiManager not available for episode analysis"}
            
            # Perform episode analysis based on the analysis type
            if analysis_type == "narrative_flow":
                # Analyze narrative flow across episodes
                result = await self._analyze_narrative_flow(story_id, user_id, episode_range)
            elif analysis_type == "character_development":
                # Analyze character development across episodes
                result = await self._analyze_character_development(story_id, user_id, episode_range)
            elif analysis_type == "plot_progression":
                # Analyze plot progression across episodes
                result = await self._analyze_plot_progression(story_id, user_id, episode_range)
            elif analysis_type == "thematic_analysis":
                # Analyze themes across episodes
                result = await self._analyze_themes(story_id, user_id, episode_range)
            elif analysis_type == "pacing_analysis":
                # Analyze pacing across episodes
                result = await self._analyze_pacing(story_id, user_id, episode_range)
            else:
                return {"error": f"Unknown analysis type: {analysis_type}"}
            
            return {
                "story_id": story_id,
                "analysis_type": analysis_type,
                "episode_range": episode_range,
                "timestamp": datetime.utcnow().isoformat(),
                "results": result
            }
            
        except Exception as e:
            return {"error": str(e), "story_id": story_id, "analysis_type": analysis_type}
    
    async def relationship_evolution(self, story_id: str, user_id: str, character_pairs: Optional[List[Dict[str, str]]] = None, 
                                    time_range: Optional[Dict[str, str]] = None, evolution_metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """Track and analyze how character relationships evolve over time and story episodes."""
        try:
            if not self.graphiti_manager:
                return {"error": "GraphitiManager not available for relationship evolution analysis"}
            
            # Use the tier-2 template for relationship milestones
            if character_pairs:
                # Analyze specific character pairs
                evolution_data = []
                for pair in character_pairs:
                    pair_result = await self.optimized_query(
                        "relationship_milestones_over_time",
                        {
                            "story_id": story_id,
                            "user_id": user_id,
                            "character_a": pair["character_a"],
                            "character_b": pair["character_b"],
                            "start_time": time_range.get("start_time") if time_range else None,
                            "end_time": time_range.get("end_time") if time_range else None
                        }
                    )
                    evolution_data.append({
                        "character_pair": pair,
                        "evolution": pair_result.get("data", [])
                    })
            else:
                # Analyze all relationships
                all_relationships_query = """
                    MATCH (c1:Character)-[r:RELATIONSHIP]-(c2:Character)
                    WHERE c1.story_id = $story_id AND ($user_id IS NULL OR c1.user_id = $user_id)
                    RETURN DISTINCT c1.name as character_a, c2.name as character_b
                """
                pairs_result = await self.graph_query(all_relationships_query, {"story_id": story_id, "user_id": user_id})
                evolution_data = await self._analyze_all_relationship_evolution(story_id, user_id, pairs_result.get("data", []), time_range)
            
            return {
                "story_id": story_id,
                "character_pairs": character_pairs or "all",
                "time_range": time_range,
                "evolution_metrics": evolution_metrics,
                "timestamp": datetime.utcnow().isoformat(),
                "evolution_data": evolution_data
            }
            
        except Exception as e:
            return {"error": str(e), "story_id": story_id}
    
    async def sna_overview(self, story_id: str, user_id: str, network_scope: str, scope_parameters: Optional[Dict[str, Any]] = None,
                          analysis_metrics: Optional[List[str]] = None, relationship_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform Social Network Analysis (SNA) to provide overview of character relationship networks and social dynamics."""
        try:
            if not self.graphiti_manager:
                return {"error": "GraphitiManager not available for SNA analysis"}
            
            # Build network based on scope
            if network_scope == "full_story":
                network_data = await self._build_full_story_network(story_id, user_id, relationship_filters)
            elif network_scope == "episode_range":
                episodes = scope_parameters.get("episodes", []) if scope_parameters else []
                network_data = await self._build_episode_range_network(story_id, user_id, episodes, relationship_filters)
            elif network_scope == "character_centric":
                central_character = scope_parameters.get("central_character") if scope_parameters else None
                degrees = scope_parameters.get("degrees_of_separation", 2) if scope_parameters else 2
                network_data = await self._build_character_centric_network(story_id, user_id, central_character, degrees, relationship_filters)
            else:
                return {"error": f"Unknown network scope: {network_scope}"}
            
            # Calculate requested SNA metrics
            sna_metrics = {}
            if analysis_metrics:
                for metric in analysis_metrics:
                    if metric == "centrality":
                        sna_metrics["centrality"] = await self._calculate_centrality(network_data)
                    elif metric == "clustering":
                        sna_metrics["clustering"] = await self._calculate_clustering(network_data)
                    elif metric == "community_detection":
                        sna_metrics["communities"] = await self._detect_communities(network_data)
                    elif metric == "influence_paths":
                        sna_metrics["influence_paths"] = await self._analyze_influence_paths(network_data)
                    elif metric == "network_density":
                        sna_metrics["network_density"] = await self._calculate_network_density(network_data)
                    elif metric == "bridge_characters":
                        sna_metrics["bridge_characters"] = await self._identify_bridge_characters(network_data)
            
            return {
                "story_id": story_id,
                "network_scope": network_scope,
                "scope_parameters": scope_parameters,
                "relationship_filters": relationship_filters,
                "timestamp": datetime.utcnow().isoformat(),
                "network_data": network_data,
                "sna_metrics": sna_metrics
            }
            
        except Exception as e:
            return {"error": str(e), "story_id": story_id, "network_scope": network_scope}
    
    # === HELPER METHODS FOR NEW TOOLS ===
    
    async def _analyze_narrative_flow(self, story_id: str, user_id: str, episode_range: Optional[Dict[str, int]]) -> Dict[str, Any]:
        """Analyze narrative flow across episodes."""
        # Implementation for narrative flow analysis
        return {"narrative_flow": "Analysis of story progression, pacing, and coherence across episodes"}
    
    async def _analyze_character_development(self, story_id: str, user_id: str, episode_range: Optional[Dict[str, int]]) -> Dict[str, Any]:
        """Analyze character development across episodes."""
        # Implementation for character development analysis
        return {"character_development": "Analysis of character growth and change across episodes"}
    
    async def _analyze_plot_progression(self, story_id: str, user_id: str, episode_range: Optional[Dict[str, int]]) -> Dict[str, Any]:
        """Analyze plot progression across episodes."""
        # Implementation for plot progression analysis
        return {"plot_progression": "Analysis of plot advancement and story structure across episodes"}
    
    async def _analyze_themes(self, story_id: str, user_id: str, episode_range: Optional[Dict[str, int]]) -> Dict[str, Any]:
        """Analyze themes across episodes."""
        # Implementation for thematic analysis
        return {"thematic_analysis": "Analysis of recurring themes and motifs across episodes"}
    
    async def _analyze_pacing(self, story_id: str, user_id: str, episode_range: Optional[Dict[str, int]]) -> Dict[str, Any]:
        """Analyze pacing across episodes."""
        # Implementation for pacing analysis
        return {"pacing_analysis": "Analysis of story pacing and rhythm across episodes"}
    
    async def _analyze_all_relationship_evolution(self, story_id: str, user_id: str, character_pairs: List[Dict], time_range: Optional[Dict[str, str]]) -> List[Dict]:
        """Analyze evolution for all character relationships."""
        evolution_data = []
        for pair in character_pairs:
            try:
                pair_result = await self.optimized_query(
                    "relationship_milestones_over_time",
                    {
                        "story_id": story_id,
                        "user_id": user_id,
                        "character_a": pair["character_a"],
                        "character_b": pair["character_b"],
                        "start_time": time_range.get("start_time") if time_range else None,
                        "end_time": time_range.get("end_time") if time_range else None
                    }
                )
                evolution_data.append({
                    "character_pair": pair,
                    "evolution": pair_result.get("data", [])
                })
            except Exception as e:
                evolution_data.append({
                    "character_pair": pair,
                    "error": str(e)
                })
        return evolution_data
    
    async def _build_full_story_network(self, story_id: str, user_id: str, relationship_filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build social network for the entire story."""
        # Implementation for full story network building
        return {"network_type": "full_story", "nodes": [], "edges": []}
    
    async def _build_episode_range_network(self, story_id: str, user_id: str, episodes: List[int], relationship_filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build social network for specific episode range."""
        # Implementation for episode range network building
        return {"network_type": "episode_range", "episodes": episodes, "nodes": [], "edges": []}
    
    async def _build_character_centric_network(self, story_id: str, user_id: str, central_character: str, degrees: int, relationship_filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build character-centric social network."""
        # Implementation for character-centric network building
        return {"network_type": "character_centric", "central_character": central_character, "degrees": degrees, "nodes": [], "edges": []}
    
    async def _calculate_centrality(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate centrality metrics for network nodes using Neo4j GDS."""
        if not self.graphiti_manager:
            return {}

        story_id = network_data.get("story_id")
        user_id = network_data.get("user_id")
        try:
            centrality_result = await self.graphiti_manager.compute_centrality(story_id, user_id)
            metrics = centrality_result.get("centrality_metrics", {}) if centrality_result.get("status") == "success" else {}

            closeness_query = f"""
            CALL gds.graph.project.cypher(
                'closeness-{story_id}',
                'MATCH (n:Character) WHERE n.story_id = "{story_id}" AND n.user_id = "{user_id}" RETURN id(n) AS id',
                'MATCH (a:Character)-[r:FRIENDS_WITH|KNOWS|ACQUAINTED_WITH]->(b:Character)\n                 WHERE a.story_id = "{story_id}" AND a.user_id = "{user_id}"\n                 RETURN id(a) AS source, id(b) AS target, r.sna_weight AS weight'
            )
            YIELD graphName
            CALL gds.closeness.stream('closeness-{story_id}')
            YIELD nodeId, score
            MATCH (n) WHERE id(n) = nodeId
            RETURN n.name AS character, score AS closeness_centrality
            ORDER BY score DESC
            """

            closeness_results = await self.graphiti_manager._run_cypher_query(closeness_query)
            cleanup_query = f"CALL gds.graph.drop('closeness-{story_id}') YIELD graphName"
            await self.graphiti_manager._run_cypher_query(cleanup_query)

            return {
                "degree_centrality": metrics.get("degree_centrality", []),
                "betweenness_centrality": metrics.get("betweenness_centrality", []),
                "closeness_centrality": closeness_results,
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _calculate_clustering(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate clustering coefficients using Neo4j GDS triangle count."""
        if not self.graphiti_manager:
            return {}

        story_id = network_data.get("story_id")
        user_id = network_data.get("user_id")

        try:
            local_query = f"""
            CALL gds.graph.project.cypher(
                'cluster-{story_id}',
                'MATCH (n:Character) WHERE n.story_id = "{story_id}" AND n.user_id = "{user_id}" RETURN id(n) AS id',
                'MATCH (a:Character)-[r:FRIENDS_WITH|KNOWS|ACQUAINTED_WITH]->(b:Character)\n                 WHERE a.story_id = "{story_id}" AND a.user_id = "{user_id}"\n                 RETURN id(a) AS source, id(b) AS target, r.sna_weight AS weight'
            )
            YIELD graphName
            CALL gds.triangleCount.stream('cluster-{story_id}')
            YIELD nodeId, clusteringCoefficient
            MATCH (n) WHERE id(n) = nodeId
            RETURN n.name AS character, clusteringCoefficient
            ORDER BY clusteringCoefficient DESC
            """

            stats_query = f"CALL gds.triangleCount.stats('cluster-{story_id}') YIELD globalClusteringCoefficient RETURN globalClusteringCoefficient"

            local_results = await self.graphiti_manager._run_cypher_query(local_query)
            stats_result = await self.graphiti_manager._run_cypher_query(stats_query)
            cleanup_query = f"CALL gds.graph.drop('cluster-{story_id}') YIELD graphName"
            await self.graphiti_manager._run_cypher_query(cleanup_query)

            return {
                "global_clustering": stats_result[0].get("globalClusteringCoefficient", 0.0) if stats_result else 0.0,
                "local_clustering": {r["character"]: r["clusteringCoefficient"] for r in local_results},
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _detect_communities(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect communities in the character network using GDS Louvain."""
        if not self.graphiti_manager:
            return {}

        story_id = network_data.get("story_id")
        user_id = network_data.get("user_id")

        try:
            result = await self.graphiti_manager.detect_communities(story_id, user_id)
            return result.get("community_detection", {}) if result.get("status") == "success" else {"error": result.get("error")}
        except Exception as e:
            return {"error": str(e)}
    
    async def _analyze_influence_paths(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze influence paths and key influencers using GDS algorithms."""
        if not self.graphiti_manager:
            return {}

        story_id = network_data.get("story_id")
        user_id = network_data.get("user_id")

        try:
            path_query = f"""
            CALL gds.graph.project.cypher(
                'influence-{story_id}',
                'MATCH (n:Character) WHERE n.story_id = "{story_id}" AND n.user_id = "{user_id}" RETURN id(n) AS id',
                'MATCH (a:Character)-[r:FRIENDS_WITH|KNOWS|ACQUAINTED_WITH]->(b:Character)\n                 WHERE a.story_id = "{story_id}" AND a.user_id = "{user_id}"\n                 RETURN id(a) AS source, id(b) AS target, r.sna_weight AS weight'
            )
            YIELD graphName
            CALL gds.allShortestPaths.dijkstra.stream('influence-{story_id}')
            YIELD sourceNodeId, targetNodeId, distance
            WITH gds.util.asNode(sourceNodeId) AS src, gds.util.asNode(targetNodeId) AS dst, distance
            RETURN src.name AS from, dst.name AS to, distance
            ORDER BY distance ASC
            LIMIT 20
            """

            influencer_query = f"""
            CALL gds.pageRank.stream('influence-{story_id}')
            YIELD nodeId, score
            MATCH (n) WHERE id(n) = nodeId
            RETURN n.name AS character, score
            ORDER BY score DESC
            LIMIT 5
            """

            paths = await self.graphiti_manager._run_cypher_query(path_query)
            influencers = await self.graphiti_manager._run_cypher_query(influencer_query)
            cleanup_query = f"CALL gds.graph.drop('influence-{story_id}') YIELD graphName"
            await self.graphiti_manager._run_cypher_query(cleanup_query)

            return {"influence_paths": paths, "key_influencers": influencers}
        except Exception as e:
            return {"error": str(e)}
    
    async def _calculate_network_density(self, network_data: Dict[str, Any]) -> float:
        """Calculate overall network density using Neo4j GDS."""
        if not self.graphiti_manager:
            return 0.0

        story_id = network_data.get("story_id")
        user_id = network_data.get("user_id")

        try:
            density_query = f"""
            CALL gds.graph.project.cypher(
                'density-{story_id}',
                'MATCH (n:Character) WHERE n.story_id = "{story_id}" AND n.user_id = "{user_id}" RETURN id(n) AS id',
                'MATCH (a:Character)-[r:FRIENDS_WITH|KNOWS|ACQUAINTED_WITH]-(b:Character)\n                 WHERE a.story_id = "{story_id}" AND a.user_id = "{user_id}"\n                 RETURN id(a) AS source, id(b) AS target'
            )
            YIELD graphName
            CALL gds.graph.density('density-{story_id}')
            YIELD density
            RETURN density
            """

            result = await self.graphiti_manager._run_cypher_query(density_query)
            cleanup_query = f"CALL gds.graph.drop('density-{story_id}') YIELD graphName"
            await self.graphiti_manager._run_cypher_query(cleanup_query)

            return result[0].get("density", 0.0) if result else 0.0
        except Exception:
            return 0.0
    
    async def _identify_bridge_characters(self, network_data: Dict[str, Any]) -> List[str]:
        """Identify bridge characters using betweenness centrality."""
        if not self.graphiti_manager:
            return []

        story_id = network_data.get("story_id")
        user_id = network_data.get("user_id")

        try:
            bridge_query = f"""
            CALL gds.graph.project.cypher(
                'bridge-{story_id}',
                'MATCH (n:Character) WHERE n.story_id = "{story_id}" AND n.user_id = "{user_id}" RETURN id(n) AS id',
                'MATCH (a:Character)-[r:FRIENDS_WITH|KNOWS|ACQUAINTED_WITH]-(b:Character)\n                 WHERE a.story_id = "{story_id}" AND a.user_id = "{user_id}"\n                 RETURN id(a) AS source, id(b) AS target'
            )
            YIELD graphName
            CALL gds.betweenness.stream('bridge-{story_id}')
            YIELD nodeId, score
            MATCH (n) WHERE id(n) = nodeId
            RETURN n.name AS character
            ORDER BY score DESC
            LIMIT 10
            """

            result = await self.graphiti_manager._run_cypher_query(bridge_query)
            cleanup_query = f"CALL gds.graph.drop('bridge-{story_id}') YIELD graphName"
            await self.graphiti_manager._run_cypher_query(cleanup_query)

            return [r["character"] for r in result]
        except Exception:
            return []
