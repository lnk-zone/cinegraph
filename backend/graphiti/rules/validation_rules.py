"""
Validation Rules Engine
======================

This module implements pre-write triggers and validation rules for the Graphiti knowledge graph.
It ensures data integrity by blocking invalid edges before they are created.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from graphiti_core import Graphiti


class ValidationRules:
    """
    Validation rules engine that implements pre-write triggers and constraints
    for the Graphiti knowledge graph.
    """
    
    def __init__(self, graphiti: Graphiti):
        self.graphiti = graphiti
        self.rules = {}
        self._setup_rules()
    
    def _setup_rules(self):
        """Setup all validation rules and triggers"""
        self.rules = {
            'prevent_invalid_knows_edges': self._prevent_invalid_knows_edges,
            'prevent_relationship_self_loops': self._prevent_relationship_self_loops,
            'validate_temporal_consistency': self._validate_temporal_consistency,
            'validate_ownership_temporal_logic': self._validate_ownership_temporal_logic,
            'validate_scene_order': self._validate_scene_order
        }
    
    async def validate_edge_creation(self, edge_type: str, from_node: Dict[str, Any], 
                                   to_node: Dict[str, Any], properties: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate edge creation before it's committed to the graph.
        
        Args:
            edge_type: Type of edge being created
            from_node: Source node data
            to_node: Target node data  
            properties: Edge properties
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Run all applicable validation rules
        for rule_name, rule_func in self.rules.items():
            try:
                is_valid, error_msg = await rule_func(edge_type, from_node, to_node, properties)
                if not is_valid:
                    return False, f"Rule '{rule_name}' failed: {error_msg}"
            except Exception as e:
                return False, f"Rule '{rule_name}' encountered error: {str(e)}"
        
        return True, ""

    async def _validate_ownership_temporal_logic(self, edge_type: str, from_node: Dict[str, Any], 
                                               to_node: Dict[str, Any], properties: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that ownership_start <= ownership_end if both are provided.
        """
        if edge_type != "OWNS":
            return True, ""
        
        ownership_start = properties.get('ownership_start')
        ownership_end = properties.get('ownership_end')

        if ownership_start and ownership_end:
            if isinstance(ownership_start, str):
                ownership_start = datetime.fromisoformat(ownership_start)
            if isinstance(ownership_end, str):
                ownership_end = datetime.fromisoformat(ownership_end)

            if ownership_start > ownership_end:
                return False, "ownership_start cannot be after ownership_end"

        return True, ""
    
    async def _prevent_invalid_knows_edges(self, edge_type: str, from_node: Dict[str, Any], 
                                         to_node: Dict[str, Any], properties: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Prevent creation of KNOWS edges where knowledge is learned before the character was created.
        
        This rule ensures temporal consistency in character knowledge:
        - Character must exist before they can learn something
        - Knowledge must be valid when learned
        """
        if edge_type != "KNOWS":
            return True, ""
        
        # Get character creation time
        character_created_at = from_node.get('created_at')
        if not character_created_at:
            return False, "Character must have creation timestamp"
        
        # Get knowledge validity period
        knowledge_valid_from = to_node.get('valid_from')
        if not knowledge_valid_from:
            return False, "Knowledge must have valid_from timestamp"
        
        # Convert to datetime objects for comparison
        if isinstance(character_created_at, str):
            character_created_at = datetime.fromisoformat(character_created_at)
        if isinstance(knowledge_valid_from, str):
            knowledge_valid_from = datetime.fromisoformat(knowledge_valid_from)
        
        # Check if knowledge is valid after character creation
        if knowledge_valid_from < character_created_at:
            return False, f"Knowledge valid from {knowledge_valid_from} but character created at {character_created_at}"
        
        return True, ""
    
    async def _prevent_relationship_self_loops(self, edge_type: str, from_node: Dict[str, Any], 
                                             to_node: Dict[str, Any], properties: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Prevent creation of RELATIONSHIP edges that create self-loops.
        
        Characters cannot have relationships with themselves.
        """
        if edge_type != "RELATIONSHIP":
            return True, ""
        
        # Get node IDs
        from_id = from_node.get('character_id') or from_node.get('id')
        to_id = to_node.get('character_id') or to_node.get('id')
        
        if not from_id or not to_id:
            return False, "Both nodes must have valid IDs"
        
        # Check for self-loop
        if from_id == to_id:
            return False, f"Self-loop detected: character {from_id} cannot have relationship with itself"
        
        return True, ""
    
    async def _validate_temporal_consistency(self, edge_type: str, from_node: Dict[str, Any], 
                                           to_node: Dict[str, Any], properties: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate temporal consistency for all edges with temporal properties.
        
        Ensures that:
        - created_at <= updated_at
        - valid_from <= valid_to (for knowledge)
        - Event times are logical
        """
        # Check edge properties for temporal consistency
        created_at = properties.get('created_at')
        updated_at = properties.get('updated_at')
        
        if created_at and updated_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at)
            
            if created_at > updated_at:
                return False, "created_at cannot be after updated_at"
        
        # Special validation for knowledge validity periods
        if edge_type == "KNOWS":
            valid_from = to_node.get('valid_from')
            valid_to = to_node.get('valid_to')
            
            if valid_from and valid_to:
                if isinstance(valid_from, str):
                    valid_from = datetime.fromisoformat(valid_from)
                if isinstance(valid_to, str):
                    valid_to = datetime.fromisoformat(valid_to)
                
                if valid_from > valid_to:
                    return False, "Knowledge valid_from cannot be after valid_to"
        
        return True, ""
    
    async def _validate_scene_order(self, edge_type: str, from_node: Dict[str, Any], 
                                  to_node: Dict[str, Any], properties: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate scene ordering for PRESENT_IN edges.
        
        Ensures that scene_order values are sequential and logical.
        """
        if edge_type != "PRESENT_IN":
            return True, ""
        
        # Get scene order
        scene_order = to_node.get('scene_order')
        if scene_order is None:
            return False, "Scene must have scene_order"
        
        # Validate scene order is positive
        if scene_order < 0:
            return False, "Scene order must be non-negative"
        
        # TODO: Could add additional validation here to check for gaps in scene ordering
        # This would require querying existing scenes in the graph
        
        return True, ""
    
    async def register_triggers(self):
        """
        Register all validation triggers with the Graphiti instance.
        
        This method sets up pre-write hooks that will be called before
        any edge is created in the graph.
        """
        # Register the main validation trigger
        await self.graphiti.register_trigger(
            trigger_name="edge_validation",
            trigger_type="BEFORE_CREATE_EDGE",
            callback=self.validate_edge_creation
        )
        
        print("Validation triggers registered successfully")
    
    async def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about validation rule execution.
        
        Returns:
            Dictionary containing validation statistics
        """
        # This would typically query the graphiti instance for stats
        # For now, return placeholder stats
        return {
            "total_validations": 0,
            "failed_validations": 0,
            "rules_enabled": len(self.rules),
            "active_triggers": ["edge_validation"]
        }


class ValidationError(Exception):
    """Custom exception for validation rule failures"""
    
    def __init__(self, rule_name: str, message: str):
        self.rule_name = rule_name
        self.message = message
        super().__init__(f"Validation rule '{rule_name}' failed: {message}")
