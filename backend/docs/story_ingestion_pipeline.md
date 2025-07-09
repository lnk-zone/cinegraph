# Story Ingestion Pipeline Implementation

## Overview

This document describes the implementation of Step 5 of the CineGraph project: the story ingestion pipeline that processes raw story content using Graphiti's extraction capabilities to identify entities, relationships, and temporal data within a <300ms target for 2K words.

## Architecture

### Components

#### 1. StoryProcessor Class

**Location**: `core/story_processor.py`

The main class responsible for processing story content and extracting structured data.

**Key Features**:
- Splits story content into manageable scenes/paragraphs
- Uses Graphiti's episodic memory and fact extraction for entity/relationship extraction
- Maps extracted data to the CineGraph schema (Character, Scene, Location, Knowledge)
- Maintains traceability mappings between text segments and scene IDs
- Tracks processing statistics and performance metrics

**Methods**:
- `process_story(content, story_id)`: Main processing method
- `_split_into_scenes(content)`: Splits text into processable segments
- `_extract_with_graphiti(scenes, story_id)`: Extracts entities using Graphiti
- `_map_and_upsert_entities(extracted_data, story_id)`: Maps to schema and upserts
- `_store_traceability_mappings(scenes, extracted_data)`: Maintains traceability
- `get_processing_stats()`: Returns performance statistics
- `get_traceability_mapping(segment_id)`: Retrieves scene mapping

#### 2. GraphitiManager Integration

**Location**: `core/graphiti_manager.py`

Enhanced to support story ingestion pipeline requirements:
- Session management for story isolation
- Fact extraction using `extract_facts()` method
- Entity and relationship upserting through `upsert_entity()` and `upsert_relationship()`
- Episodic memory management with `add_episode()`

## Processing Pipeline

### Step 1: Scene Splitting

The raw story content is split into manageable scenes using:
- Double newlines (`\n\n`)
- Scene markers (`---`, `***`)
- Each scene gets a unique ID and metadata

```python
scenes = [
    {
        "id": "scene_1_abc123",
        "text": "The hero enters the forest...",
        "order": 1,
        "word_count": 25,
        "segment_id": "segment_1"
    },
    # ... more scenes
]
```

### Step 2: Graphiti Extraction

For each scene:
1. **Episode Creation**: Use `add_episode()` to create episodic memory entry
2. **Fact Extraction**: Use `extract_facts()` to identify entities and relationships
3. **Entity Processing**: Convert facts into structured entities and relationships

```python
# Example extraction result
facts = [
    {
        "fact": "Hero enters the ancient forest",
        "entities": ["Hero", "ancient forest"],
        "confidence": 0.85
    }
]
```

### Step 3: Schema Mapping

Transform extracted facts into CineGraph schema:

**Entity Types**:
- `CHARACTER`: People, NPCs, protagonists
- `LOCATION`: Places, rooms, geographical features
- `ITEM`: Objects, weapons, tools
- `EVENT`: Actions, battles, meetings
- `KNOWLEDGE`: Facts, information, lore
- `SCENE`: Story segments, chapters

**Relationship Types**:
- `KNOWS`: Character-knowledge relationships
- `LOCATED_AT`: Entity-location relationships
- `PARTICIPATES_IN`: Character-event relationships
- `PRESENT_IN`: Entity-scene relationships

### Step 4: Traceability Mapping

Maintain mappings for debugging and analysis:
- `segment_id` → `scene_id`
- `entity_id` → `scene_id` (where mentioned)

Example:
```python
mappings = {
    "segment_1": "scene_1_abc123",
    "segment_2": "scene_2_def456",
    "entity_hero_xyz": "scene_1_abc123"
}
```

## Performance Optimization

### Target: <300ms for 2K words

**Optimization Strategies**:

1. **Async Processing**: All operations are asynchronous
2. **Connection Reuse**: Shared GraphitiManager instance
3. **Batch Operations**: Process multiple scenes efficiently
4. **Smart Chunking**: Optimal scene size for processing
5. **Caching**: Reuse session and connection objects

### Performance Monitoring

Built-in statistics tracking:
- Total stories processed
- Average processing time
- Last processing timestamp
- Per-story performance metrics

## Data Flow

```
Raw Story Content
       ↓
Scene Splitting
       ↓
Graphiti Extraction (per scene)
       ↓
Fact Processing
       ↓
Schema Mapping
       ↓
Entity/Relationship Upserting
       ↓
Traceability Storage
       ↓
Performance Tracking
```

## Usage Examples

### Basic Usage

```python
from core.story_processor import StoryProcessor
from core.graphiti_manager import GraphitiManager

# Initialize
graphiti_manager = GraphitiManager()
await graphiti_manager.initialize()

story_processor = StoryProcessor(graphiti_manager=graphiti_manager)

# Process story
story_content = "The hero enters the forest..."
story_id = "story_001"

result = await story_processor.process_story(story_content, story_id)

# Access results
entities = result["entities"]
relationships = result["relationships"]
scenes = result["scenes"]
knowledge_items = result["knowledge_items"]
traceability = result["traceability_mappings"]
```

### API Integration

```python
@app.post("/api/story/analyze")
async def analyze_story(story_input: StoryInput):
    result = await story_processor.process_story(
        story_input.content, 
        story_input.story_id
    )
    return {
        "status": "success",
        "extracted_data": result,
        "story_id": story_input.story_id
    }
```

## Testing

### Unit Tests

Run the basic functionality test:
```bash
python test_story_ingestion.py
```

### Performance Benchmarks

Test performance against the <300ms target:
```bash
python benchmark_story_ingestion.py
```

The benchmark tests various word counts and measures:
- Average processing time
- Min/max processing times
- Words per second throughput
- Target compliance

## Error Handling

**Common Error Scenarios**:
- Graphiti connection failures
- Malformed story content
- Extraction timeouts
- Schema mapping errors

**Error Response Format**:
```python
{
    "error": "Description of error",
    "processing_time_ms": 150.5,
    "processed_at": "2024-01-15T10:30:00Z",
    "story_id": "story_001"
}
```

## Future Enhancements

### Planned Optimizations

1. **Parallel Scene Processing**: Process independent scenes concurrently
2. **Caching Layer**: Cache extracted entities to avoid re-processing
3. **Streaming Processing**: Process large stories in chunks
4. **Smart Batching**: Group related scenes for batch processing
5. **Custom NLP Models**: Train domain-specific entity extraction models

### Monitoring and Analytics

1. **Performance Metrics Dashboard**: Real-time processing statistics
2. **Entity Recognition Accuracy**: Track extraction quality
3. **Processing Bottleneck Analysis**: Identify performance issues
4. **Story Complexity Metrics**: Analyze content difficulty

## Implementation Status

✅ **Completed**:
- Core story ingestion pipeline
- Graphiti integration with fact extraction
- Schema mapping for all entity types
- Traceability mapping system
- Performance monitoring
- Error handling and recovery
- Basic testing framework

🔄 **In Progress**:
- Performance optimization for <300ms target
- Comprehensive test coverage
- Advanced entity type detection

📋 **Planned**:
- Parallel processing implementation
- Advanced caching strategies
- Custom NLP model integration
- Real-time monitoring dashboard

## Configuration

### Environment Variables

```bash
# Graphiti Database Configuration
GRAPHITI_DATABASE_URL=bolt://localhost:7687
GRAPHITI_DATABASE_USER=neo4j
GRAPHITI_DATABASE_PASSWORD=password
GRAPHITI_DATABASE_NAME=neo4j
GRAPHITI_MAX_CONNECTIONS=10
GRAPHITI_CONNECTION_TIMEOUT=30
```

### Performance Tuning

```python
# Adjust scene splitting patterns
SCENE_SPLIT_PATTERNS = [
    r'\n\s*\n',           # Double newlines
    r'\n\s*---\s*\n',     # Triple dashes
    r'\n\s*\*\*\*\s*\n'   # Triple asterisks
]

# Entity type detection keywords
ENTITY_TYPE_KEYWORDS = {
    "LOCATION": ["castle", "town", "forest", "mountain"],
    "CHARACTER": ["hero", "villain", "knight", "wizard"],
    "ITEM": ["sword", "potion", "key", "ring"]
}
```

## Conclusion

The story ingestion pipeline successfully implements the requirements of Step 5, providing:

1. **Efficient Processing**: Targets <300ms for 2K words
2. **Comprehensive Extraction**: Entities, relationships, and temporal data
3. **Schema Compliance**: Maps to CineGraph data model
4. **Traceability**: Maintains source-to-scene mappings
5. **Performance Monitoring**: Built-in statistics and benchmarking

The implementation leverages Graphiti's powerful extraction capabilities while maintaining the flexibility and performance requirements of the CineGraph application.
