#!/usr/bin/env python3
"""
Migration 002: Add New Relationships and Properties
=======================================

This migration script adds new relationship types with additional properties
and necessary indexes and uniqueness constraints.

Usage:
    python migration_002_add_new_relationships.py
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path to import graphiti
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from graphiti_core import Graphiti

class NewRelationshipsMigration:
    """Migration class for adding new relationships and properties"""

    def __init__(self, graphiti_instance: Graphiti):
        self.graphiti = graphiti_instance

    async def up(self):
        """Apply the migration - add new relationships and properties"""
        print("Adding new relationships and properties...")

        # Add new relationships
        await self._add_relationships()

        # Add constraints
        await self._add_constraints()

        print("New relationships and properties added successfully!")

    async def _add_relationships(self):
        """Add new relationships"""

        # INTERACTS_WITH relationship (Character -> Character)
        interacts_with_schema = {
            "type": "INTERACTS_WITH",
            "from": "Character",
            "to": "Character",
            "properties": {
                "interactionWeight": {"type": "integer"},
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True}
            }
        }

        # SHARES_SCENE (Character -> Character)
        shares_scene_schema = {
            "type": "SHARES_SCENE",
            "from": "Character",
            "to": "Character",
            "properties": {
                "screenTimeOverlap": {"type": "integer"},
                "created_at": {"type": "datetime", "temporal": True},
                "updated_at": {"type": "datetime", "temporal": True}
            }
        }

        # Create new relationships
        relationships = [interacts_with_schema, shares_scene_schema]

        for rel in relationships:
            await self.graphiti.create_relationship_type(rel)
            print(f"Created relationship: {rel['type']}")

    async def _add_constraints(self):
        """Add additional constraints and indexes"""

        # Index and constraints for new properties
        await self.graphiti.create_constraint("Character", "interactionWeight", "INDEX")
        await self.graphiti.create_constraint("Character", "screenTimeOverlap", "INDEX")

        print("Created all constraints and indexes")

async def main():
    """Main migration function"""
    
    # Get connection parameters from environment
    uri = os.getenv('GRAPHITI_DATABASE_URL')
    user = os.getenv('GRAPHITI_DATABASE_USER')
    password = os.getenv('GRAPHITI_DATABASE_PASSWORD')
    
    if not all([uri, user, password]):
        raise ValueError("Missing required environment variables: GRAPHITI_DATABASE_URL, GRAPHITI_DATABASE_USER, GRAPHITI_DATABASE_PASSWORD")
    
    # Initialize Graphiti instance
    graphiti = Graphiti(uri, user, password)
    await graphiti.initialize()

    # Create migration instance
    migration = NewRelationshipsMigration(graphiti)
    
    # Apply the migration
    await migration.up()
    
    # Close connection
    await graphiti.close()

if __name__ == "__main__":
    asyncio.run(main())

