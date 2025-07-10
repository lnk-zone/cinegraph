# Refactor get_nodes_by_query Strategy

## Overview

This document provides a comprehensive strategy for refactoring all `get_nodes_by_query()` usage in the codebase, classifying each occurrence and mapping it to appropriate replacement approaches using Graphiti's episodic APIs.

**Total occurrences analyzed: 10**  
**Files affected: 4**  
**Generated on: 2025-07-10**

## Usage Classification

### Category 1: Production Logic → Episodic APIs (1 occurrence)

These are production code patterns that should be refactored to use Graphiti's episodic memory system for statistics and operational queries.

| File | Line | Current Usage | Classification |
|------|------|---------------|----------------|
| `core/graphiti_manager.py` | 116 | `get_nodes_by_query("MATCH (n) RETURN count(n) as node_count LIMIT 1")` | **Production statistics** |

### Category 2: Diagnostics/Admin Tooling → Guarded Helpers (9 occurrences)

These are debug, testing, and administrative queries that can remain as direct Cypher but should be wrapped in guarded helper methods.

| File | Line | Current Usage | Classification |
|------|------|---------------|----------------|
| `debug_neo4j_transactions.py` | 84 | CREATE and RETURN test node | **Debug - Node creation testing** |
| `debug_neo4j_transactions.py` | 91 | MATCH test nodes verification | **Debug - Persistence verification** |
| `debug_neo4j_transactions.py` | 98 | Total node count | **Debug - Database state** |
| `debug_graphiti_methods_detailed.py` | 81 | Direct node creation bypass | **Debug - API testing** |
| `debug_graphiti_methods_detailed.py` | 86 | Node count verification | **Debug - Creation verification** |
| `debug_proper_relationships.py` | 29 | Node count overview | **Debug - Database overview** |
| `debug_proper_relationships.py` | 33 | Relationship count overview | **Debug - Database overview** |
| `debug_proper_relationships.py` | 87 | Post-operation node count | **Debug - State verification** |
| `debug_proper_relationships.py` | 91 | Post-operation relationship count | **Debug - State verification** |
| `debug_proper_relationships.py` | 95 | Relationship type analysis | **Debug - Schema analysis** |

## Refactoring Design Matrix

### Production Logic Replacements

| Old Query Pattern | New Approach | Implementation Strategy |
|-------------------|--------------|-------------------------|
| `MATCH (n) RETURN count(n)` | **Episodic Statistics** | Replace with `get_query_statistics()` method that aggregates from episodic memory |

**Detailed Implementation:**

```python
# OLD: Direct node counting
result = await self.client.get_nodes_by_query("MATCH (n) RETURN count(n) as node_count LIMIT 1")
node_count = len(result) if result else 0

# NEW: Episodic statistics
stats = await self.get_query_statistics()
node_count = stats.get('episode_count', 0)
```

### Diagnostic/Admin Tooling Replacements

| Query Category | Old Pattern | New Approach | Implementation |
|----------------|-------------|--------------|----------------|
| **Database Health** | Direct node/relationship counts | **Guarded Helper** | `GraphitiAdminHelper.get_database_stats()` |
| **Node Creation Testing** | CREATE queries for testing | **Guarded Helper** | `GraphitiAdminHelper.create_test_node()` |
| **State Verification** | MATCH queries for verification | **Guarded Helper** | `GraphitiAdminHelper.verify_state()` |
| **Schema Analysis** | Relationship type queries | **Guarded Helper** | `GraphitiAdminHelper.analyze_schema()` |

## Implementation Plan

### Phase 1: Create Guarded Helper Class

Create `GraphitiAdminHelper` class with administrative methods:

```python
class GraphitiAdminHelper:
    """Administrative helper for direct Cypher queries with proper safeguards."""
    
    def __init__(self, client, enable_direct_queries: bool = False):
        self.client = client
        self.enabled = enable_direct_queries
        
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics - guarded admin method."""
        if not self.enabled:
            raise RuntimeError("Direct queries disabled. Use episodic APIs instead.")
        
        return await self.client.get_nodes_by_query(
            "MATCH (n) OPTIONAL MATCH ()-[r]->() RETURN count(n) as nodes, count(r) as relationships"
        )
    
    async def verify_state(self, query: str) -> List[Dict[str, Any]]:
        """Execute verification query - guarded admin method."""
        if not self.enabled:
            raise RuntimeError("Direct queries disabled. Use episodic APIs instead.")
        
        return await self.client.get_nodes_by_query(query)
```

### Phase 2: Refactor Production Code

**File: `core/graphiti_manager.py`**

```python
# Replace health check method
async def health_check(self) -> Dict[str, Any]:
    """Health check using episodic memory statistics."""
    try:
        if not self.client:
            return {"status": "disconnected", "error": "No client connection"}
        
        # Use episodic statistics instead of direct query
        stats = await self.get_query_statistics()
        
        return {
            "status": "healthy",
            "database_url": self.config.database_url,
            "database_name": self.config.database_name,
            "episode_count": stats.get('episode_count', 0),
            "session_count": stats.get('session_count', 0),
            "connection_timeout": self.config.connection_timeout
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database_url": self.config.database_url if hasattr(self, 'config') else "unknown"
        }
```

### Phase 3: Refactor Debug Files

**Create debug helper method:**

```python
async def debug_with_admin_helper(self, query: str, description: str):
    """Execute debug query with proper safeguards."""
    admin_helper = GraphitiAdminHelper(self.client, enable_direct_queries=True)
    
    try:
        result = await admin_helper.verify_state(query)
        print(f"✅ {description}: {result}")
        return result
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return None
```

**Update debug files to use helper:**

```python
# Replace direct get_nodes_by_query calls with helper
result = await self.debug_with_admin_helper(
    "MATCH (n) RETURN count(n) as count",
    "Database node count"
)
```

## Migration Checklist

### Production Code (Priority 1)
- [ ] Update `GraphitiManager.health_check()` to use `get_query_statistics()`
- [ ] Test health check with episodic memory
- [ ] Verify backward compatibility

### Debug/Admin Tooling (Priority 2)
- [ ] Create `GraphitiAdminHelper` class with safeguards
- [ ] Update `debug_neo4j_transactions.py` to use helper
- [ ] Update `debug_graphiti_methods_detailed.py` to use helper
- [ ] Update `debug_proper_relationships.py` to use helper
- [ ] Add configuration flag for enabling direct queries

### Testing & Validation (Priority 3)
- [ ] Add unit tests for new helper methods
- [ ] Test episodic statistics accuracy
- [ ] Verify debug functionality with guarded helpers
- [ ] Performance testing of new approaches

## Benefits of This Approach

### For Production Code:
1. **Episodic Memory Alignment**: Statistics come from the same system storing the data
2. **Consistency**: No discrepancy between episodic and direct query results
3. **Performance**: Potentially faster than scanning entire database
4. **Scalability**: Better suited for large datasets

### For Debug/Admin Code:
1. **Controlled Access**: Direct queries only when explicitly enabled
2. **Backward Compatibility**: Existing debug logic preserved
3. **Clear Separation**: Production vs. administrative code paths
4. **Safety**: Prevents accidental production use of direct queries

## Configuration

Add environment variable to control direct query access:

```bash
# Enable direct queries for debugging (default: false)
GRAPHITI_ENABLE_DIRECT_QUERIES=true
```

## Risk Mitigation

1. **Gradual Migration**: Implement helpers first, then migrate usage
2. **Feature Flags**: Use configuration to enable/disable direct queries
3. **Comprehensive Testing**: Validate episodic statistics accuracy
4. **Rollback Plan**: Keep old methods as deprecated fallbacks initially

---

**Next Steps:**
1. Implement `GraphitiAdminHelper` class
2. Update `GraphitiManager.health_check()` method
3. Create configuration system for direct query access
4. Begin systematic migration of debug files
