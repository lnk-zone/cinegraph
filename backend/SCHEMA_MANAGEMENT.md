# CineGraph Schema Management

This document explains how to synchronize the Neo4j database schema with CineGraphAgent requirements using the bootstrap script and admin endpoints.

## Overview

The CineGraphAgent requires specific indexes, constraints, and properties to function optimally with story data isolation, temporal queries, and enum validation. The schema management system ensures the live Graphiti database matches these requirements.

## Files

### `neo4j_bootstrap.cypher`
Comprehensive Cypher script that creates:
- **Node Constraints**: Unique constraints for entity integrity
- **Data Isolation Indexes**: `story_id` and `user_id` indexes for multi-tenancy
- **Temporal Indexes**: Support for bi-temporal queries (`valid_from`, `valid_to`, `created_at`, `updated_at`)
- **Enum Property Indexes**: Performance indexes for enumerated values
- **Relationship Indexes**: Comprehensive relationship property indexing
- **Graphiti-Specific Indexes**: Support for episodic memory and group operations
- **Full-Text Indexes**: Content search capabilities

### Admin Endpoints

#### `POST /api/admin/ensure_schema`
- **Purpose**: Apply the bootstrap script to synchronize schema
- **Security**: Requires authentication, development environment only
- **Function**: Reads `neo4j_bootstrap.cypher` and executes all statements
- **Returns**: Detailed execution results with success/failure counts

#### `GET /api/admin/schema_status`  
- **Purpose**: Check current schema compatibility with CineGraphAgent
- **Security**: Requires authentication, development environment only
- **Function**: Analyzes existing constraints and indexes
- **Returns**: Compatibility score and recommendations

## Usage

### 1. Check Current Schema Status

```bash
curl -X GET "http://localhost:8000/api/admin/schema_status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response Example:**
```json
{
  "endpoint": "admin_schema_status",
  "user_id": "user-123",
  "environment": "development",
  "schema_status": "incompatible",
  "compatibility_score": 30,
  "constraints_count": 2,
  "indexes_count": 8,
  "cinegraph_requirements": {
    "story_id_indexes": false,
    "user_id_indexes": false,
    "temporal_indexes": false
  },
  "recommendations": [
    "Add story_id indexes for data isolation",
    "Add user_id indexes for multi-tenancy",
    "Add temporal indexes for bi-temporal queries",
    "Add unique constraints for entity integrity"
  ],
  "timestamp": "2025-01-10T04:17:07Z",
  "note": "Run /api/admin/ensure_schema to synchronize schema with CineGraphAgent requirements"
}
```

### 2. Apply Schema Synchronization

```bash
curl -X POST "http://localhost:8000/api/admin/ensure_schema" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response Example:**
```json
{
  "endpoint": "admin_ensure_schema",
  "user_id": "user-123", 
  "environment": "development",
  "schema_sync_result": {
    "status": "completed",
    "total_statements": 95,
    "successful": 95,
    "failed": 0,
    "errors": [],
    "timestamp": "2025-01-10T04:17:07Z",
    "note": "Schema synchronization completed. Database now matches CineGraphAgent requirements."
  },
  "timestamp": "2025-01-10T04:17:07Z"
}
```

### 3. Verify Schema After Synchronization

Re-run the status check to confirm all requirements are met:

```bash
curl -X GET "http://localhost:8000/api/admin/schema_status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected Response After Sync:**
```json
{
  "schema_status": "compatible",
  "compatibility_score": 100,
  "constraints_count": 8,
  "indexes_count": 95,
  "cinegraph_requirements": {
    "story_id_indexes": true,
    "user_id_indexes": true,
    "temporal_indexes": true
  },
  "recommendations": [
    "Schema appears complete for CineGraphAgent requirements"
  ]
}
```

## Schema Components Created

### 1. Node Constraints (10 total)
```cypher
-- Unique primary keys
CREATE CONSTRAINT character_id_unique FOR (c:Character) REQUIRE c.character_id IS UNIQUE;
CREATE CONSTRAINT knowledge_id_unique FOR (k:Knowledge) REQUIRE k.knowledge_id IS UNIQUE;
CREATE CONSTRAINT scene_id_unique FOR (s:Scene) REQUIRE s.scene_id IS UNIQUE;
CREATE CONSTRAINT location_id_unique FOR (l:Location) REQUIRE l.location_id IS UNIQUE;
CREATE CONSTRAINT item_id_unique FOR (i:Item) REQUIRE i.item_id IS UNIQUE;

-- Composite unique constraints for data isolation
CREATE CONSTRAINT character_name_per_story FOR (c:Character) REQUIRE (c.name, c.story_id, c.user_id) IS UNIQUE;
CREATE CONSTRAINT location_name_per_story FOR (l:Location) REQUIRE (l.name, l.story_id, l.user_id) IS UNIQUE;
CREATE CONSTRAINT scene_order_per_story FOR (s:Scene) REQUIRE (s.scene_order, s.story_id, s.user_id) IS UNIQUE;
CREATE CONSTRAINT item_name_per_story FOR (i:Item) REQUIRE (i.name, i.story_id, i.user_id) IS UNIQUE;

-- Required content
CREATE CONSTRAINT knowledge_content_required FOR (k:Knowledge) REQUIRE k.content IS NOT NULL;
```

### 2. Data Isolation Indexes (20 total)
```cypher
-- Story ID indexes
CREATE INDEX story_id_character FOR (c:Character) ON (c.story_id);
CREATE INDEX story_id_knowledge FOR (k:Knowledge) ON (k.story_id);
CREATE INDEX story_id_scene FOR (s:Scene) ON (s.story_id);
CREATE INDEX story_id_location FOR (l:Location) ON (l.story_id);
CREATE INDEX story_id_item FOR (i:Item) ON (i.story_id);

-- User ID indexes  
CREATE INDEX user_id_character FOR (c:Character) ON (c.user_id);
CREATE INDEX user_id_knowledge FOR (k:Knowledge) ON (k.user_id);
CREATE INDEX user_id_scene FOR (s:Scene) ON (s.user_id);
CREATE INDEX user_id_location FOR (l:Location) ON (l.user_id);
CREATE INDEX user_id_item FOR (i:Item) ON (i.user_id);

-- Combined story+user indexes
CREATE INDEX story_user_character FOR (c:Character) ON (c.story_id, c.user_id);
CREATE INDEX story_user_knowledge FOR (k:Knowledge) ON (k.story_id, k.user_id);
CREATE INDEX story_user_scene FOR (s:Scene) ON (s.story_id, s.user_id);
CREATE INDEX story_user_location FOR (l:Location) ON (l.story_id, l.user_id);
CREATE INDEX story_user_item FOR (i:Item) ON (i.story_id, i.user_id);
```

### 3. Temporal Indexes (20 total)
Support for bi-temporal queries on all entities:
```cypher
-- Valid time indexes
CREATE INDEX temporal_valid_from_character FOR (c:Character) ON (c.valid_from);
CREATE INDEX temporal_valid_to_character FOR (c:Character) ON (c.valid_to);
CREATE INDEX temporal_valid_from_knowledge FOR (k:Knowledge) ON (k.valid_from);
CREATE INDEX temporal_valid_to_knowledge FOR (k:Knowledge) ON (k.valid_to);

-- Transaction time indexes
CREATE INDEX temporal_created_at_character FOR (c:Character) ON (c.created_at);
CREATE INDEX temporal_updated_at_character FOR (c:Character) ON (c.updated_at);
CREATE INDEX temporal_created_at_item FOR (i:Item) ON (i.created_at);
CREATE INDEX temporal_updated_at_item FOR (i:Item) ON (i.updated_at);
```

### 4. Enum Property Indexes (10 total)
```cypher
-- Knowledge enums
CREATE INDEX knowledge_type_index FOR (k:Knowledge) ON (k.knowledge_type);
CREATE INDEX importance_level_index FOR (k:Knowledge) ON (k.importance_level);
CREATE INDEX verification_status_index FOR (k:Knowledge) ON (k.verification_status);

-- Location enums
CREATE INDEX location_type_index FOR (l:Location) ON (l.location_type);
CREATE INDEX accessibility_index FOR (l:Location) ON (l.accessibility);

-- Item enums
CREATE INDEX item_type_index FOR (i:Item) ON (i.item_type);
CREATE INDEX item_is_active_index FOR (i:Item) ON (i.is_active);
```

### 5. Relationship Indexes (30+ total)
Comprehensive indexing for all relationship properties:
```cypher
-- KNOWS relationship
CREATE INDEX knows_learned_at FOR ()-[r:KNOWS]-() ON (r.learned_at);
CREATE INDEX knows_confidence_level FOR ()-[r:KNOWS]-() ON (r.confidence_level);
CREATE INDEX knows_sharing_restrictions FOR ()-[r:KNOWS]-() ON (r.sharing_restrictions);

-- OWNS relationship
CREATE INDEX owns_start_time FOR ()-[r:OWNS]-() ON (r.ownership_start);
CREATE INDEX owns_end_time FOR ()-[r:OWNS]-() ON (r.ownership_end);
CREATE INDEX owns_transfer_method FOR ()-[r:OWNS]-() ON (r.transfer_method);

-- RELATIONSHIP relationship
CREATE INDEX relationship_type_index FOR ()-[r:RELATIONSHIP]-() ON (r.relationship_type);
CREATE INDEX relationship_strength_index FOR ()-[r:RELATIONSHIP]-() ON (r.relationship_strength);
CREATE INDEX trust_level_index FOR ()-[r:RELATIONSHIP]-() ON (r.trust_level);

-- Data isolation for relationships
CREATE INDEX relationship_story_id FOR ()-[r:KNOWS]-() ON (r.story_id);
CREATE INDEX relationship_user_id FOR ()-[r:KNOWS]-() ON (r.user_id);
```

## Environment Security

### Development Only
The admin endpoints are restricted to development environments:
- Checks `ENVIRONMENT` environment variable
- Only allows: `development`, `dev`, `local`
- Returns 403 Forbidden in production environments

### Authentication Required
- Uses JWT authentication via `get_authenticated_user`
- Requires valid Supabase JWT token
- Logs user ID for audit trails

## Troubleshooting

### Common Issues

#### 1. Missing `story_id` Property Warning
```
{severity: WARNING} {code: Neo.ClientNotification.Statement.UnknownPropertyKeyWarning} 
{description: One of the property names in your query is not available in the database, make sure you didn't misspell it or that the label is available when you run this statement in your application (the missing property name is: story_id)}
```

**Solution**: Run `/api/admin/ensure_schema` to create the missing property indexes.

#### 2. Schema Compatibility Score Low
If compatibility score is below 80%, run the schema synchronization:
```bash
curl -X POST "http://localhost:8000/api/admin/ensure_schema" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 3. Permission Denied in Production
```json
{
  "detail": "Schema management endpoint only available in development environment"
}
```

**Solution**: Set `ENVIRONMENT=development` or use the endpoints only in development.

#### 4. Bootstrap Script Not Found
```json
{
  "error": "Bootstrap script not found at /path/to/neo4j_bootstrap.cypher"
}
```

**Solution**: Ensure `neo4j_bootstrap.cypher` exists in the backend root directory.

## Manual Schema Application

If you prefer to apply the schema manually:

1. **Using Neo4j Browser:**
   - Open Neo4j Browser
   - Copy contents of `neo4j_bootstrap.cypher`
   - Execute the script

2. **Using Cypher Shell:**
   ```bash
   cypher-shell -u neo4j -p password < neo4j_bootstrap.cypher
   ```

3. **Using Python:**
   ```python
   from graphiti_core import Graphiti
   
   client = Graphiti(uri="bolt://localhost:7687", user="neo4j", password="password")
   
   with open("neo4j_bootstrap.cypher", "r") as f:
       script = f.read()
   
   # Execute statements individually
   ```

## Performance Impact

### Index Creation Time
- **Small databases** (\u003c1M nodes): 1-5 minutes
- **Medium databases** (1M-10M nodes): 5-30 minutes  
- **Large databases** (\u003e10M nodes): 30+ minutes

### Query Performance Improvements
After schema synchronization:
- **Data isolation queries**: 10-100x faster
- **Temporal queries**: 5-50x faster
- **Enum filtering**: 2-10x faster
- **Full-text search**: Available

### Storage Overhead
- **Indexes**: ~10-20% additional storage
- **Constraints**: Minimal overhead
- **Overall impact**: 10-25% storage increase for 10-100x query performance

## Monitoring

### Schema Health Check
Include schema status in your monitoring:

```python
async def monitor_schema_health():
    status = await admin_schema_status()
    
    if status["compatibility_score"] \u003c 80:
        # Alert: Schema needs synchronization
        logger.warning(f"Schema compatibility low: {status['compatibility_score']}")
    
    return status
```

### Performance Metrics
Monitor query performance before and after schema application:
- Query execution times
- Index usage statistics
- Constraint violation counts

## Best Practices

1. **Regular Schema Checks**: Run status checks in CI/CD pipelines
2. **Backup Before Changes**: Always backup before applying schema changes
3. **Test in Staging**: Apply schema changes to staging environment first
4. **Monitor Performance**: Track query performance after schema changes
5. **Version Control**: Keep `neo4j_bootstrap.cypher` in version control
6. **Environment Separation**: Never run schema management in production

## Support

For issues with schema synchronization:
1. Check the endpoint response for detailed error messages
2. Verify Neo4j connection and permissions
3. Ensure `neo4j_bootstrap.cypher` is present and readable
4. Check environment variable configuration
5. Review Neo4j logs for constraint/index creation errors

The schema management system ensures CineGraphAgent operates at optimal performance with proper data isolation, temporal support, and query optimization.
