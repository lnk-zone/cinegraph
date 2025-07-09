# Graphiti Rules Engine

The Graphiti Rules Engine provides validation and consistency enforcement for knowledge graphs built with Graphiti. It includes pre-write triggers, Cypher-based consistency rules, and background jobs for maintaining graph integrity.

## Features

- **Pre-write Triggers**: Block invalid edges before they're created
- **Cypher Rules**: Detect contradictions using graph queries
- **Background Jobs**: Periodic consistency scanning
- **Comprehensive Testing**: Full test suite with pytest-asyncio

## Components

### 1. ValidationRules

Pre-write triggers that validate edge creation before committing to the graph.

#### Rules Implemented:
- `prevent_invalid_knows_edges`: Blocks KNOWS edges where knowledge is learned before character creation
- `prevent_relationship_self_loops`: Prevents characters from having relationships with themselves
- `validate_temporal_consistency`: Ensures temporal properties are logical
- `validate_scene_order`: Validates scene ordering for PRESENT_IN edges

#### Usage:
```python
from graphiti.rules.validation_rules import ValidationRules

# Initialize with Graphiti instance
validation_rules = ValidationRules(graphiti)

# Register triggers
await validation_rules.register_triggers()

# Validate edge creation
is_valid, error_msg = await validation_rules.validate_edge_creation(
    edge_type="KNOWS",
    from_node=character_data,
    to_node=knowledge_data,
    properties=edge_properties
)
```

### 2. ConsistencyEngine

Cypher-based rules for detecting contradictions in the knowledge graph.

#### Rules Implemented:
- `detect_temporal_contradictions`: Finds temporal conflicts in knowledge
- `detect_relationship_contradictions`: Finds conflicting relationship states
- `detect_location_contradictions`: Finds location-based contradictions
- `detect_character_state_contradictions`: Finds character state conflicts
- `find_unlinked_contradictions`: Finds general content contradictions

#### Usage:
```python
from graphiti.rules.consistency_engine import ConsistencyEngine

# Initialize with Graphiti instance
consistency_engine = ConsistencyEngine(graphiti)

# Run consistency scan
await consistency_engine.run_consistency_scan()

# Get contradiction report
report = await consistency_engine.get_contradiction_report()
```

### 3. BackgroundConsistencyJob

Background job that runs consistency checks at regular intervals.

#### Features:
- Configurable run interval
- Automatic error handling
- Status reporting
- Manual trigger support

#### Usage:
```python
from graphiti.rules.background_jobs import BackgroundConsistencyJob

# Initialize with custom interval (default: 1 hour)
background_job = BackgroundConsistencyJob(graphiti, run_interval=3600)

# Start background job
await background_job.start()

# Run manual scan
await background_job.run_once()

# Get status
status = await background_job.get_status()

# Stop background job
await background_job.stop()
```

## Installation

The rules engine is part of the Graphiti project. Ensure you have the required dependencies:

```bash
pip install graphiti-core pytest pytest-asyncio
```

## Testing

Run the complete test suite:

```bash
python -m pytest tests/ -v
```

Run specific test files:

```bash
# Test validation rules
python -m pytest tests/test_validation_rules.py -v

# Test consistency engine
python -m pytest tests/test_consistency_engine.py -v

# Test background jobs
python -m pytest tests/test_background_jobs.py -v
```

## Examples

See `examples/rules_usage_example.py` for a comprehensive demonstration of all features.

## Rule Details

### ValidationRules

#### prevent_invalid_knows_edges
Ensures characters can only learn knowledge that is valid after their creation time.

**Validation:**
- Character must have `created_at` timestamp
- Knowledge must have `valid_from` timestamp
- `knowledge.valid_from >= character.created_at`

**Example:**
```python
# Valid: Character created before knowledge becomes valid
character = {'created_at': '2023-01-01T10:00:00'}
knowledge = {'valid_from': '2023-01-01T12:00:00'}
# Result: ✓ PASS

# Invalid: Character created after knowledge became valid
character = {'created_at': '2023-01-01T15:00:00'}
knowledge = {'valid_from': '2023-01-01T10:00:00'}
# Result: ✗ FAIL - "Knowledge valid from ... but character created at ..."
```

#### prevent_relationship_self_loops
Prevents characters from having relationships with themselves.

**Validation:**
- Only applies to RELATIONSHIP edges
- Compares `from_node.character_id` with `to_node.character_id`

**Example:**
```python
# Valid: Different characters
from_node = {'character_id': 'char_1'}
to_node = {'character_id': 'char_2'}
# Result: ✓ PASS

# Invalid: Same character
from_node = {'character_id': 'char_1'}
to_node = {'character_id': 'char_1'}
# Result: ✗ FAIL - "Self-loop detected: character char_1 cannot have relationship with itself"
```

#### validate_temporal_consistency
Ensures temporal properties are in logical order.

**Validation:**
- `created_at <= updated_at`
- `valid_from <= valid_to` (for knowledge)

**Example:**
```python
# Valid: Proper temporal order
properties = {
    'created_at': '2023-01-01T10:00:00',
    'updated_at': '2023-01-01T11:00:00'
}
# Result: ✓ PASS

# Invalid: Temporal contradiction
properties = {
    'created_at': '2023-01-01T11:00:00',
    'updated_at': '2023-01-01T10:00:00'
}
# Result: ✗ FAIL - "created_at cannot be after updated_at"
```

#### validate_scene_order
Validates scene ordering for PRESENT_IN edges.

**Validation:**
- Only applies to PRESENT_IN edges
- `scene_order >= 0`

**Example:**
```python
# Valid: Non-negative scene order
to_node = {'scene_order': 1}
# Result: ✓ PASS

# Invalid: Negative scene order
to_node = {'scene_order': -1}
# Result: ✗ FAIL - "Scene order must be non-negative"
```

### ConsistencyEngine Cypher Rules

#### detect_temporal_contradictions
Finds cases where knowledge timeline creates contradictions.

**Cypher Query:**
```cypher
MATCH (c:Character)-[:KNOWS]->(k1:Knowledge)
MATCH (c)-[:KNOWS]->(k2:Knowledge)
WHERE k1.knowledge_id <> k2.knowledge_id
AND k1.valid_from > k2.valid_to
AND k1.content CONTAINS k2.content
AND NOT EXISTS((k1)-[:CONTRADICTS]->(k2))
AND NOT EXISTS((k2)-[:CONTRADICTS]->(k1))
RETURN k1.knowledge_id as from_id, k2.knowledge_id as to_id, 
       'temporal' as severity, 
       'Knowledge timeline contradiction' as reason,
       0.8 as confidence
```

#### detect_relationship_contradictions
Finds conflicting relationship states between characters.

**Cypher Query:**
```cypher
MATCH (c1:Character)-[r1:RELATIONSHIP]->(c2:Character)
MATCH (c1)-[r2:RELATIONSHIP]->(c2)
WHERE r1.relationship_type <> r2.relationship_type
AND r1.created_at < r2.created_at
AND NOT EXISTS((c1)-[:CONTRADICTS]-(c2))
RETURN c1.character_id + '_' + r1.relationship_type as from_id,
       c1.character_id + '_' + r2.relationship_type as to_id,
       'medium' as severity,
       'Conflicting relationship types' as reason,
       0.9 as confidence
```

#### detect_location_contradictions
Finds cases where characters appear in multiple locations simultaneously.

**Cypher Query:**
```cypher
MATCH (c:Character)-[:PRESENT_IN]->(s1:Scene)-[:OCCURS_IN]->(l1:Location)
MATCH (c)-[:PRESENT_IN]->(s2:Scene)-[:OCCURS_IN]->(l2:Location)
WHERE s1.scene_order = s2.scene_order
AND l1.location_id <> l2.location_id
AND NOT EXISTS((s1)-[:CONTRADICTS]-(s2))
RETURN s1.scene_id as from_id, s2.scene_id as to_id,
       'high' as severity,
       'Character in multiple locations simultaneously' as reason,
       0.95 as confidence
```

#### detect_character_state_contradictions
Finds contradictory character states (e.g., dead/alive).

**Cypher Query:**
```cypher
MATCH (c:Character)-[:KNOWS]->(k1:Knowledge)
MATCH (c)-[:KNOWS]->(k2:Knowledge)
WHERE k1.knowledge_id <> k2.knowledge_id
AND k1.content CONTAINS 'dead' 
AND k2.content CONTAINS 'alive'
AND abs(duration.between(k1.valid_from, k2.valid_from).seconds) < 3600
AND NOT EXISTS((k1)-[:CONTRADICTS]->(k2))
RETURN k1.knowledge_id as from_id, k2.knowledge_id as to_id,
       'critical' as severity,
       'Character state contradiction (dead/alive)' as reason,
       0.99 as confidence
```

#### find_unlinked_contradictions
Finds general content contradictions that haven't been marked.

**Cypher Query:**
```cypher
MATCH (k1:Knowledge), (k2:Knowledge)
WHERE k1.knowledge_id <> k2.knowledge_id
AND NOT EXISTS((k1)-[:CONTRADICTS]->(k2))
AND NOT EXISTS((k2)-[:CONTRADICTS]->(k1))
AND (
    (k1.content CONTAINS 'not' AND k2.content CONTAINS substring(k1.content, 4))
    OR (k1.content CONTAINS 'dead' AND k2.content CONTAINS 'alive')
    OR (k1.content CONTAINS 'enemy' AND k2.content CONTAINS 'friend')
)
RETURN k1.knowledge_id as from_id, k2.knowledge_id as to_id,
       'medium' as severity,
       'Content contradiction detected' as reason,
       0.7 as confidence
```

## Error Handling

The rules engine includes comprehensive error handling:

1. **Validation Errors**: Caught and returned as error messages
2. **Cypher Execution Errors**: Logged and don't stop other rules
3. **Background Job Errors**: Logged with automatic retry logic
4. **Custom Exceptions**: `ValidationError` for rule-specific failures

## Performance Considerations

- **Triggers**: Run synchronously during edge creation
- **Consistency Scans**: Run asynchronously in background
- **Query Optimization**: Cypher queries use indexes and constraints
- **Error Recovery**: Failed rules don't block other validations

## Contributing

To add new validation rules:

1. Add the rule method to `ValidationRules` class
2. Register it in `_setup_rules()`
3. Add comprehensive tests
4. Update documentation

To add new consistency rules:

1. Add the Cypher query method to `ConsistencyEngine`
2. Register it in `_setup_cypher_rules()`
3. Add tests for the query structure
4. Update documentation

## License

This project is part of the Graphiti ecosystem and follows the same licensing terms.
