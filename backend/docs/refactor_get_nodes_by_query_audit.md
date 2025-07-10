# Refactor get_nodes_by_query Audit

This document provides a comprehensive audit of all `get_nodes_by_query()` usage in the repository as of the current state. This serves as a reference for the refactoring process.

## Overview

Total occurrences found: **10**
Files affected: **4**

## Detailed Usage Analysis

| File Path | Line No | Code Excerpt | Purpose |
|-----------|---------|--------------|---------|
| `backend/debug_neo4j_transactions.py` | 84 | `result = await manager.client.get_nodes_by_query("""CREATE (g:GraphitiTest {...}) RETURN g.name as name""")` | Debug - Testing Graphiti query execution |
| `backend/debug_neo4j_transactions.py` | 91 | `check_result = await manager.client.get_nodes_by_query("""MATCH (g:GraphitiTest) RETURN g.name as name, g.created as created""")` | Debug - Immediate check for test node persistence |
| `backend/debug_neo4j_transactions.py` | 98 | `count_result = await manager.client.get_nodes_by_query("MATCH (n) RETURN count(n) as count")` | Debug - Get total node count for verification |
| `backend/debug_graphiti_methods_detailed.py` | 81 | `direct_result = await client.get_nodes_by_query(test_query)` | Debug - Test direct node creation bypass |
| `backend/debug_graphiti_methods_detailed.py` | 86 | `check_result = await client.get_nodes_by_query(check_query)` | Debug - Check TestEntity node count |
| `backend/debug_proper_relationships.py` | 29 | `overview_result = await manager.client.get_nodes_by_query(overview_query)` | Debug - Get current node count overview |
| `backend/debug_proper_relationships.py` | 33 | `rel_overview_result = await manager.client.get_nodes_by_query(rel_overview_query)` | Debug - Get current relationship count overview |
| `backend/debug_proper_relationships.py` | 87 | `nodes_after = await manager.client.get_nodes_by_query("MATCH (n) RETURN count(n) as count")` | Debug - Check node count after community building |
| `backend/debug_proper_relationships.py` | 91 | `rels_after = await manager.client.get_nodes_by_query("MATCH ()-[r]->() RETURN count(r) as count")` | Debug - Check relationship count after community building |
| `backend/debug_proper_relationships.py` | 95 | `rel_types = await manager.client.get_nodes_by_query("MATCH ()-[r]->() RETURN DISTINCT type(r) as rel_type, count(r) as count")` | Debug - Get relationship types and counts |
| `backend/debug_proper_relationships.py` | 101 | `sample_rels = await manager.client.get_nodes_by_query("""MATCH (a)-[r]->(b) RETURN type(r) as rel_type, ...""")` | Debug - Sample relationships with properties |
| `backend/core/graphiti_manager.py` | 116 | `result = await self.client.get_nodes_by_query("MATCH (n) RETURN count(n) as node_count LIMIT 1")` | Health-check - Test connection and get node count |

## Purpose Classification

### Debug Usage (9 occurrences)
- **Files**: `debug_neo4j_transactions.py`, `debug_graphiti_methods_detailed.py`, `debug_proper_relationships.py`
- **Purpose**: Testing, verification, and investigation of Graphiti functionality
- **Queries**: Node creation, counting, relationship analysis, database state checking

### Health-check Usage (1 occurrence)
- **File**: `core/graphiti_manager.py`
- **Purpose**: Connection validation and basic database health monitoring
- **Query**: Simple node count to verify database connectivity

### Stats Usage (0 occurrences)
- No pure statistics gathering usage found

### Business Logic Usage (0 occurrences)
- No core business logic usage found

## Query Pattern Analysis

### Query Types Used:
1. **Node Creation**: `CREATE (n:Label {...}) RETURN n.property`
2. **Node Counting**: `MATCH (n) RETURN count(n) as count`
3. **Relationship Counting**: `MATCH ()-[r]->() RETURN count(r) as count`
4. **Relationship Analysis**: `MATCH ()-[r]->() RETURN DISTINCT type(r), count(r)`
5. **Relationship Sampling**: `MATCH (a)-[r]->(b) RETURN type(r), properties...`

### Error Handling Patterns:
- Most usage is wrapped in try-catch blocks
- Debug files use basic error printing
- Health-check has defensive error handling with fallback values

## Context Analysis

### Debug Files Context:
- All debug files are investigating Graphiti 0.3.0 functionality
- Focus on transaction handling, method availability, and relationship creation
- Used for troubleshooting and understanding API behavior

### Production Code Context:
- Single usage in `GraphitiManager.health_check()` method
- Used as a simple connectivity test
- Has proper error handling and returns status information

## Recommendations for Refactoring

1. **Debug Files**: Consider whether these should be kept as-is for debugging purposes or updated to use new API patterns
2. **Health-check**: This is the only production usage and should be prioritized for refactoring
3. **Query Patterns**: Most queries are simple and should be straightforward to refactor
4. **Error Handling**: Existing error handling patterns should be preserved in refactored code

## Notes

- All usage appears to be compatible with Graphiti 0.3.0 API
- No complex query patterns that would be difficult to refactor
- Most usage is for debugging/testing rather than core functionality
- The single production usage is well-contained and straightforward to refactor

---

*Generated on: $(date)*
*Repository state: Current working directory*
*Total files scanned: 4*
*Total occurrences: 10*
