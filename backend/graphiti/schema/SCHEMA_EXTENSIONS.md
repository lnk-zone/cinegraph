# Cinegraph Schema Extensions - Episode Entities and SNA Optimizations

## Overview

This document describes the extensions made to the cinegraph schema to support hierarchical narrative structure through Episode entities and enhanced Social Network Analysis (SNA) capabilities.

## Schema Extensions

### 1. New Episode Entity

The `Episode` entity represents narrative story segments with different hierarchical types:

```json
{
  "name": "Episode",
  "description": "Represents narrative story segments of different hierarchical types",
  "properties": {
    "episode_id": {"type": "string", "unique": true, "required": true},
    "title": {"type": "string"},
    "episode_type": {"type": "enum", "values": ["Arc", "Chapter", "Thread"]},
    "pov_character_id": {"type": "string"},
    "mood": {"type": "string"},
    "significance_score": {"type": "integer", "min": 0, "max": 10},
    "timestamp_in_story": {"type": "timestamp"},
    // ... standard temporal and metadata properties
  }
}
```

#### Episode Types:
- **Arc**: Major story arcs spanning multiple chapters
- **Chapter**: Individual chapters or major scenes
- **Thread**: Specific narrative threads or subplots

#### Key Properties:
- `episode_type`: Defines the hierarchical level (Arc > Chapter > Thread)
- `pov_character_id`: References the primary point-of-view character
- `mood`: Textual description of the episode's emotional tone
- `significance_score`: Numeric rating (0-10) of the episode's importance to the overall story

### 2. Hierarchical Relationships

#### PARENT_OF
Defines hierarchical relationships between episodes:
- Arc PARENT_OF Chapter
- Chapter PARENT_OF Thread
- Enables tree-like narrative structure

### 3. Continuity Relationships

#### CALLBACKS_TO
Connects episodes that reference past events:
- Links current episodes to previous story elements
- Tracks narrative callbacks and references

#### FORESHADOWS
Connects episodes that hint at future events:
- Links setup episodes to payoff episodes
- Tracks narrative foreshadowing

#### RESOLVES
Connects episodes that resolve previous events:
- Links resolution episodes to setup episodes
- Tracks narrative closure and completion

### 4. Episode-Entity Relationships

#### CONTAINS (Episode → Scene)
Links episodes to the scenes they contain:
- `scene_order`: Order of scenes within the episode

#### FEATURES (Episode → Character)
Links episodes to prominently featured characters:
- `prominence_level`: 1-10 rating of character importance in episode
- `character_arc_stage`: Description of character development stage

### 5. Enhanced Character Relationships

Extended the `RELATIONSHIP` edge between characters with:

```json
{
  "milestone": {"type": "string"},
  "trigger_event_id": {"type": "string"},
  "secret_level": {"type": "integer", "min": 0, "max": 10}
}
```

#### New Properties:
- `milestone`: Describes significant relationship milestones
- `trigger_event_id`: References events that triggered relationship changes
- `secret_level`: 0-10 rating of how secret the relationship is

### 6. Analytics and SNA Optimizations

#### Projection Labels
Added `REL_INDEX(character_id)` for optimized Social Network Analysis queries.

#### Indexes for Performance
Created comprehensive indexing strategy in `cinegraph_constraints.cypher`:

- **Character Network Indexes**: Optimized for centrality calculations
- **Episode Hierarchy Indexes**: Fast traversal of narrative structure
- **Temporal Indexes**: Time-based queries and analysis
- **Full-text Search**: Content discovery across episodes and relationships
- **Range Indexes**: Numeric property queries (significance, trust levels, etc.)

## Validation Rules

### Entity Validation
- Episode types must be Arc, Chapter, or Thread
- Episode significance_score must be between 0 and 10
- All existing entity validation rules maintained

### Relationship Validation
- PARENT_OF relationships cannot create circular hierarchies
- Episode continuity relationships must be temporally consistent
- Extended character relationship properties must meet validation constraints

### Consistency Rules
- Episodes must maintain temporal consistency in continuity relationships
- Character relationships must respect secret level constraints
- Hierarchical episode structures must be logically consistent

## Database Constraints

The `cinegraph_constraints.cypher` file provides:

1. **Unique Constraints**: Ensure entity ID uniqueness
2. **Property Existence**: Require essential properties
3. **Validation Constraints**: Enforce data integrity rules
4. **Performance Indexes**: Optimize query performance for SNA

## Usage Examples

### Creating Episode Hierarchy
```cypher
// Create an Arc
CREATE (arc:Episode {
  episode_id: "arc_001",
  title: "The Journey Begins",
  episode_type: "Arc",
  significance_score: 9,
  story_id: "story_001",
  user_id: "user_001"
})

// Create a Chapter within the Arc
CREATE (chapter:Episode {
  episode_id: "chapter_001",
  title: "Departure",
  episode_type: "Chapter",
  pov_character_id: "char_protagonist",
  mood: "anticipation",
  significance_score: 7,
  story_id: "story_001",
  user_id: "user_001"
})

// Link them hierarchically
CREATE (arc)-[:PARENT_OF]->(chapter)
```

### Creating Continuity Links
```cypher
// Link foreshadowing to resolution
MATCH (setup:Episode {episode_id: "chapter_001"})
MATCH (payoff:Episode {episode_id: "chapter_015"})
CREATE (setup)-[:FORESHADOWS]->(payoff)
```

### Enhanced Character Relationships
```cypher
// Create relationship with extended properties
MATCH (c1:Character {character_id: "char_001"})
MATCH (c2:Character {character_id: "char_002"})
CREATE (c1)-[:RELATIONSHIP {
  relationship_type: "ally",
  trust_level: 8,
  milestone: "Saved each other's lives",
  trigger_event_id: "event_battle_001",
  secret_level: 3
}]->(c2)
```

## Benefits

1. **Hierarchical Narrative Structure**: Organize story elements at multiple levels
2. **Enhanced Continuity Tracking**: Track foreshadowing, callbacks, and resolutions
3. **Advanced Character Analysis**: Deeper relationship modeling with secrets and milestones
4. **Optimized Performance**: Comprehensive indexing for fast SNA queries
5. **Flexible POV Tracking**: Track perspective changes throughout the narrative
6. **Significance Scoring**: Quantify episode importance for analysis

## Migration Considerations

- Existing schema remains fully compatible
- New entities and relationships are additive
- Existing queries continue to work unchanged
- Gradual migration path available for existing data
