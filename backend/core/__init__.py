"""
Core module for CineGraph backend.

This module provides the core functionality for the CineGraph application,
including the GraphitiManager for knowledge graph operations and data models.
"""

from .graphiti_manager import GraphitiManager
from .story_processor import StoryProcessor
from .models import (
    StoryInput, CharacterKnowledge, InconsistencyReport, StoryGraph,
    GraphEntity, GraphRelationship, EntityType, RelationshipType,
    InconsistencyType, Inconsistency, TemporalQuery, GraphitiConfig
)

__all__ = [
    "GraphitiManager",
    "StoryProcessor",
    "StoryInput",
    "CharacterKnowledge", 
    "InconsistencyReport",
    "StoryGraph",
    "GraphEntity",
    "GraphRelationship",
    "EntityType",
    "RelationshipType",
    "InconsistencyType",
    "Inconsistency",
    "TemporalQuery",
    "GraphitiConfig"
]
