
"""
Core Models for CineGraph Application
====================================

This module defines the Pydantic models used throughout the CineGraph application
for data validation, serialization, and API contracts.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import uuid

class ItemType(str, Enum):
    """Types of items in the knowledge graph."""
    WEAPON = "weapon"
    TOOL = "tool"
    CLOTHING = "clothing"
    ARTIFACT = "artifact"

class TransferMethod(str, Enum):
    """Methods of item transfer in the knowledge graph."""
    GIFT = "gift"
    EXCHANGE = "exchange"
    THEFT = "theft"
    INHERITANCE = "inheritance"

class ItemEntity(BaseModel):
    """Represents an item entity in the knowledge graph."""
    
    id: str = Field(..., description="Unique identifier for the item")
    type: ItemType = Field(..., description="Type of the item")
    name: str = Field(..., description="Name of the item")
    description: Optional[str] = Field(default=None, description="Description of the item")
    origin_scene: Optional[str] = Field(default=None, description="Scene where the item first appears")
    location_found: Optional[str] = Field(default=None, description="Location where the item is found")
    current_owner: Optional[str] = Field(default=None, description="Current owner of the item")
    is_active: bool = Field(default=True, description="Whether the item is actively part of the story")
    version: Optional[int] = Field(default=None, description="Version of the item schema for forward compatibility")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

class Ownership(BaseModel):
    """Represents an ownership relationship in the knowledge graph."""
    
    from_id: str = Field(..., description="Character ID who owns the item")
    to_id: str = Field(..., description="Item ID that is owned")
    ownership_start: datetime = Field(..., description="Timestamp when ownership starts")
    ownership_end: Optional[datetime] = Field(default=None, description="Timestamp when ownership ends")
    obtained_from: Optional[str] = Field(default=None, description="Who the item was obtained from")
    transfer_method: TransferMethod = Field(..., description="Method of transfer")
    ownership_notes: Optional[str] = Field(default=None, description="Additional notes about the ownership")
    version: Optional[int] = Field(default=None, description="Version of the ownership schema for forward compatibility")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")



class StoryInput(BaseModel):
    """Input model for story analysis requests."""
    
    story_id: str = Field(..., description="Unique identifier for the story")
    content: str = Field(..., description="The story content to analyze")
    user_id: Optional[str] = Field(default=None, description="User ID for data isolation")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional story metadata")


class EpisodeType(str, Enum):
    """Different types of episodes."""
    PREMIERE = "premiere"
    FINALE = "finale"
    SPECIAL = "special"
    REGULAR = "regular"

class MoodType(str, Enum):
    """Moods for episodes."""
    HAPPY = "happy"
    SAD = "sad"
    SUSPENSE = "suspense"
    DRAMATIC = "dramatic"

class RelationshipMilestone(str, Enum):
    """Milestones in relationships."""
    FIRST_MEETING = "first_meeting"
    FRIENDS = "friends"
    ENEMIES = "enemies"
    ALLIES = "allies"

class SecretLevel(str, Enum):
    """Levels of secret information."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EpisodeEntity(BaseModel):
    """Represents an episode entity in the knowledge graph."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the episode")
    type: EpisodeType = Field(..., description="Type of the episode")
    parent_id: Optional[str] = Field(default=None, description="Parent episode ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the episode")
    version: Optional[int] = Field(default=None, description="Version of the episode schema for forward compatibility")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""
    CHARACTER = "CHARACTER"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    ITEM = "ITEM"
    KNOWLEDGE = "KNOWLEDGE"
    SCENE = "SCENE"
    EPISODE = "EPISODE"


class RelationshipType(str, Enum):
    """Types of relationships in the knowledge graph."""
    KNOWS = "KNOWS"
    PRESENT_IN = "PRESENT_IN"
    RELATIONSHIP = "RELATIONSHIP"
    LOCATED_AT = "LOCATED_AT"
    HAS_ITEM = "HAS_ITEM"
    PARTICIPATES_IN = "PARTICIPATES_IN"
    OWNS = "OWNS"




class GraphEntity(BaseModel):
    """Represents an entity in the knowledge graph."""
    
    id: str = Field(..., description="Entity identifier")
    type: EntityType = Field(..., description="Type of the entity")
    name: str = Field(..., description="Entity name")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity properties")
    version: Optional[int] = Field(default=None, description="Version of the entity schema for forward compatibility")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class GraphRelationship(BaseModel):
    """Represents a relationship in the knowledge graph."""

    type: RelationshipType = Field(..., description="Type of the relationship")
    from_id: str = Field(..., description="Source entity ID")
    to_id: str = Field(..., description="Target entity ID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relationship properties")
    version: Optional[int] = Field(default=None, description="Version of the relationship schema for forward compatibility")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

class ContinuityEdge(GraphRelationship):
    """Represents an edge for continuity between story parts such as episodes."""

class CharacterRelationshipEvolution(BaseModel):
    """Tracks character relationship evolution over time."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the evolution entry")
    character_id: str = Field(..., description="Character ID")
    target_character_id: str = Field(..., description="Target character ID")
    episode_id: Optional[str] = Field(default=None, description="Episode where change occurred")
    milestone: RelationshipMilestone = Field(..., description="Milestone in the relationship")
    mood: Optional[MoodType] = Field(default=None, description="Mood during this milestone")
    secret_level: Optional[SecretLevel] = Field(default=None, description="Secret level involved")
    story_id: str = Field(..., description="Story identifier")
    version: Optional[int] = Field(default=None, description="Version of the evolution schema for forward compatibility")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the change occurred")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class CharacterKnowledge(BaseModel):
    """Represents what a character knows at a specific point in time."""
    
    character_id: str = Field(..., description="Character identifier")
    character_name: str = Field(..., description="Character name")
    knowledge_items: List[Dict[str, Any]] = Field(default_factory=list, description="List of knowledge items")
    timestamp: Optional[datetime] = Field(default=None, description="Timestamp for temporal queries")
    story_id: str = Field(..., description="Story identifier")


class InconsistencyType(str, Enum):
    """Types of story inconsistencies."""
    TEMPORAL = "TEMPORAL"
    CHARACTER_KNOWLEDGE = "CHARACTER_KNOWLEDGE"
    LOCATION = "LOCATION"
    RELATIONSHIP = "RELATIONSHIP"
    EVENT_SEQUENCE = "EVENT_SEQUENCE"


class Inconsistency(BaseModel):
    """Represents a story inconsistency."""
    
    type: InconsistencyType = Field(..., description="Type of inconsistency")
    description: str = Field(..., description="Description of the inconsistency")
    severity: str = Field(..., description="Severity level (low, medium, high)")
    entities_involved: List[str] = Field(default_factory=list, description="Entity IDs involved")
    scene_references: List[str] = Field(default_factory=list, description="Scene IDs where inconsistency occurs")
    suggested_fix: Optional[str] = Field(default=None, description="Suggested fix for the inconsistency")


class InconsistencyReport(BaseModel):
    """Report containing detected inconsistencies."""
    
    story_id: str = Field(..., description="Story identifier")
    inconsistencies: List[Inconsistency] = Field(default_factory=list, description="List of detected inconsistencies")
    total_count: int = Field(..., description="Total number of inconsistencies")
    severity_breakdown: Dict[str, int] = Field(default_factory=dict, description="Count by severity level")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")


class ContradictionSeverity(str, Enum):
    """Severity levels for contradictions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContradictionEdge(BaseModel):
    """Represents a CONTRADICTS edge between two knowledge nodes."""
    
    from_knowledge_id: str = Field(..., description="Source knowledge node ID")
    to_knowledge_id: str = Field(..., description="Target knowledge node ID")
    severity: ContradictionSeverity = Field(..., description="Severity level of the contradiction")
    reason: str = Field(..., description="Explanation of why these nodes contradict")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="When contradiction was detected")
    story_id: str = Field(..., description="Story identifier")
    rule_name: str = Field(..., description="Name of the rule that detected this contradiction")
    

class ContradictionDetectionResult(BaseModel):
    """Result of a contradiction detection scan."""
    
    story_id: str = Field(..., description="Story identifier")
    contradictions_found: List[ContradictionEdge] = Field(default_factory=list, description="List of contradictions found")
    total_contradictions: int = Field(..., description="Total number of contradictions")
    severity_breakdown: Dict[str, int] = Field(default_factory=dict, description="Count by severity level")
    scan_duration: float = Field(..., description="Duration of scan in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When scan was performed")


class StoryGraph(BaseModel):
    """Represents the complete story knowledge graph."""
    
    story_id: str = Field(..., description="Story identifier")
    entities: List[GraphEntity] = Field(default_factory=list, description="Graph entities")
    relationships: List[GraphRelationship] = Field(default_factory=list, description="Graph relationships")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Graph metadata")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")


class TemporalQuery(BaseModel):
    """Model for temporal graph queries."""
    
    timestamp: datetime = Field(..., description="Timestamp for the query")
    entity_filters: Optional[Dict[str, Any]] = Field(default=None, description="Entity filters")
    relationship_filters: Optional[Dict[str, Any]] = Field(default=None, description="Relationship filters")


class GraphitiConfig(BaseModel):
    """Configuration for Graphiti connection."""
    
    database_url: str = Field(..., description="Neo4j database URL")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    database_name: Optional[str] = Field(default="neo4j", description="Database name")
    max_connections: int = Field(default=10, description="Maximum connection pool size")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")


class UserProfile(BaseModel):
    """User profile model."""
    
    id: str = Field(..., description="User ID (UUID)")
    email: str = Field(..., description="User email address")
    full_name: Optional[str] = Field(default=None, description="User's full name")
    avatar_url: Optional[str] = Field(default=None, description="URL to user's avatar image")
    created_at: datetime = Field(..., description="Account creation timestamp")


class UserProfileUpdate(BaseModel):
    """Model for updating user profile."""
    
    full_name: Optional[str] = Field(default=None, description="User's full name")
    avatar_url: Optional[str] = Field(default=None, description="URL to user's avatar image")


class RelationshipEvolution(BaseModel):
    """Tracks the evolution of relationships over time."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the evolution entry")
    relationship_id: str = Field(..., description="ID of the relationship being tracked")
    from_character_id: str = Field(..., description="Source character ID")
    to_character_id: str = Field(..., description="Target character ID")
    relationship_type: str = Field(..., description="Type of relationship")
    strength_before: Optional[float] = Field(default=None, description="Relationship strength before change")
    strength_after: float = Field(..., description="Relationship strength after change")
    change_reason: Optional[str] = Field(default=None, description="Reason for the relationship change")
    episode_id: Optional[str] = Field(default=None, description="Episode where change occurred")
    story_id: str = Field(..., description="Story identifier")
    user_id: str = Field(..., description="User identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the change occurred")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


class EpisodeHierarchy(BaseModel):
    """Represents the hierarchical structure of episodes."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier")
    episode_id: str = Field(..., description="Episode identifier")
    parent_episode_id: Optional[str] = Field(default=None, description="Parent episode ID (for sub-episodes)")
    child_episodes: List[str] = Field(default_factory=list, description="List of child episode IDs")
    depth_level: int = Field(default=0, description="Depth in the hierarchy (0 = root level)")
    sequence_order: int = Field(..., description="Order within the same level")
    story_id: str = Field(..., description="Story identifier")
    user_id: str = Field(..., description="User identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
