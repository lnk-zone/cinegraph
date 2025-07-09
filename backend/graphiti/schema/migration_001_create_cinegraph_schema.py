#!/usr/bin/env python3
"""
Migration 001: Create CineGraph Schema
=====================================

This migration script creates the initial schema for the CineGraph system,
including four core entities and six relationships with proper temporal
handling and constraints.

Usage:
    python migration_001_create_cinegraph_schema.py
"""

import os
import sys
import asyncio
from typing import Dict, Any

# Add the parent directory to the path to import graphiti
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from graphiti_core import Graphiti


class CineGraphSchemaMigration:
    """Migration class for creating the CineGraph schema"""
    
    def __init__(self, graphiti_instance: Graphiti):
        self.graphiti = graphiti_instance
        
    async def up(self):
        """Apply the migration - create the schema"""
        print("Creating CineGraph schema...")
        
        # Create entities
        await self._create_entities()
        
        # Create relationships
        await self._create_relationships()
        
        # Create constraints
        await self._create_constraints()
        
        print("CineGraph schema created successfully!")
    
    async def down(self):
        """Rollback the migration - drop the schema"""
        print("Rolling back CineGraph schema...")
        
        # Drop relationships first (to maintain referential integrity)
        await self._drop_relationships()
        
        # Drop entities
        await self._drop_entities()
        
        print("CineGraph schema rolled back successfully!")
    
    async def _create_entities(self):
        """Create the four core entities"""
        
        # Character entity
        character_schema = {
            "name": "Character",
            "properties": {
                "character_id": {"type": "string", "unique": True, "required": True},
                "name": {"type": "string", "unique": True, "required": True},
                "description": {"type": "string"},
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True},
                "deleted_at": {"type": "datetime", "temporal": True}
            }
        }
        
        # Knowledge entity
        knowledge_schema = {
            "name": "Knowledge",
            "properties": {
                "knowledge_id": {"type": "string", "unique": True, "required": True},
                "content": {"type": "string", "required": True},
                "valid_from": {"type": "datetime", "temporal": True},
                "valid_to": {"type": "datetime", "temporal": True},
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True}
            }
        }
        
        # Scene entity
        scene_schema = {
            "name": "Scene",
            "properties": {
                "scene_id": {"type": "string", "unique": True, "required": True},
                "name": {"type": "string", "required": True},
                "scene_order": {"type": "integer", "sequential": True, "required": True},
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True}
            }
        }
        
        # Location entity
        location_schema = {
            "name": "Location",
            "properties": {
                "location_id": {"type": "string", "unique": True, "required": True},
                "name": {"type": "string", "unique": True, "required": True},
                "details": {"type": "string"},
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True}
            }
        }
        
        # Create entities
        entities = [character_schema, knowledge_schema, scene_schema, location_schema]
        for entity in entities:
            await self.graphiti.create_entity_type(entity)
            print(f"Created entity: {entity['name']}")
    
    async def _create_relationships(self):
        """Create the six core relationships"""
        
        # KNOWS relationship (Character -> Character)
        knows_schema = {
            "type": "KNOWS",
            "from": "Character",
            "to": "Character",
            "properties": {
                "intensity": {"type": "integer"},
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True}
            }
        }
        
        # RELATIONSHIP (Character -> Character)
        relationship_schema = {
            "type": "RELATIONSHIP",
            "from": "Character",
            "to": "Character",
            "properties": {
                "relationship_type": {"type": "string", "required": True},
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True}
            }
        }
        
        # PRESENT_IN (Character -> Scene)
        present_in_schema = {
            "type": "PRESENT_IN",
            "from": "Character",
            "to": "Scene",
            "properties": {
                "appearance_order": {"type": "integer"},
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True}
            }
        }
        
        # OCCURS_IN (Scene -> Location)
        occurs_in_schema = {
            "type": "OCCURS_IN",
            "from": "Scene",
            "to": "Location",
            "properties": {
                "event_time": {"type": "datetime", "temporal": True}
            }
        }
        
        # CONTRADICTS (Knowledge -> Knowledge)
        contradicts_schema = {
            "type": "CONTRADICTS",
            "from": "Knowledge",
            "to": "Knowledge",
            "properties": {
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True}
            }
        }
        
        # IMPLIES (Knowledge -> Knowledge)
        implies_schema = {
            "type": "IMPLIES",
            "from": "Knowledge",
            "to": "Knowledge",
            "properties": {
                "certainty": {"type": "integer"},
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True}
            }
        }
        
        # Create relationships
        relationships = [
            knows_schema, relationship_schema, present_in_schema,
            occurs_in_schema, contradicts_schema, implies_schema
        ]
        
        for rel in relationships:
            await self.graphiti.create_relationship_type(rel)
            print(f"Created relationship: {rel['type']}")
    
    async def _create_constraints(self):
        """Create additional constraints and indexes"""
        
        # Character constraints
        await self.graphiti.create_constraint("Character", "character_id", "UNIQUE")
        await self.graphiti.create_constraint("Character", "name", "UNIQUE")
        
        # Knowledge constraints
        await self.graphiti.create_constraint("Knowledge", "knowledge_id", "UNIQUE")
        
        # Scene constraints
        await self.graphiti.create_constraint("Scene", "scene_id", "UNIQUE")
        await self.graphiti.create_constraint("Scene", "scene_order", "SEQUENTIAL")
        
        # Location constraints
        await self.graphiti.create_constraint("Location", "location_id", "UNIQUE")
        await self.graphiti.create_constraint("Location", "name", "UNIQUE")
        
        print("Created all constraints and indexes")
    
    async def _drop_relationships(self):
        """Drop all relationships"""
        relationships = ["KNOWS", "RELATIONSHIP", "PRESENT_IN", "OCCURS_IN", "CONTRADICTS", "IMPLIES"]
        for rel in relationships:
            await self.graphiti.drop_relationship_type(rel)
            print(f"Dropped relationship: {rel}")
    
    async def _drop_entities(self):
        """Drop all entities"""
        entities = ["Character", "Knowledge", "Scene", "Location"]
        for entity in entities:
            await self.graphiti.drop_entity_type(entity)
            print(f"Dropped entity: {entity}")


async def main():
    """Main migration function"""
    
    # Initialize Graphiti instance
    graphiti = Graphiti()
    await graphiti.initialize()
    
    # Create migration instance
    migration = CineGraphSchemaMigration(graphiti)
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        await migration.down()
    else:
        await migration.up()
    
    # Close connection
    await graphiti.close()


if __name__ == "__main__":
    asyncio.run(main())
