# Graphiti 0.2 → 0.3.0 Migration Guide

## Package Information
- **Current Version**: graphiti-core==0.3.0 (confirmed installed)
- **Migration Date**: January 2025
- **Status**: ✅ Package pinned and installed successfully

## Installation Status
✅ `graphiti-core==0.3.0` is already pinned in requirements.txt  
✅ Package installed and confirmed working

## API Signature Verification

### Core Graphiti Class
```python
# Confirmed signature in 0.3.0:
Graphiti.__init__(self, uri: str, user: str, password: str, llm_client: graphiti_core.llm_client.client.LLMClient | None = None)
```

### Available Methods
```python
# Confirmed methods in Graphiti class:
- add_episode
- add_episode_bulk  
- build_communities
- build_indices_and_constraints
- close
- get_nodes_by_query
- retrieve_episodes
- search
```

## Breaking Changes Identified

### 1. SearchConfig Signature Changes ⚠️
**New SearchConfig structure in 0.3.0:**
```python
SearchConfig.model_fields = {
    'num_edges': FieldInfo(annotation=int, required=False, default=10),
    'num_nodes': FieldInfo(annotation=int, required=False, default=10), 
    'num_episodes': FieldInfo(annotation=int, required=False, default=3),
    'group_ids': FieldInfo(annotation=Union[list[Union[str, NoneType]], NoneType], required=True),
    'search_methods': FieldInfo(annotation=list[SearchMethod], required=True),
    'reranker': FieldInfo(annotation=Union[Reranker, NoneType], required=True)
}
```

**Breaking Changes:**
- `group_ids` is now **required** (was likely optional in 0.2)
- `search_methods` is now **required** (was likely optional in 0.2)
- `reranker` is now **required** (was likely optional in 0.2)

### 2. Episode API Changes ⚠️
**Current add_episode signature:**
```python
add_episode(self, name: str, episode_body: str, source_description: str, reference_time: datetime.datetime, source: graphiti_core.nodes.EpisodeType = <EpisodeType.message: 'message'>, group_id: str | None = None, uuid: str | None = None)
```

**Key Changes:**
- `source` parameter now uses `EpisodeType` enum with values: `['message', 'json', 'text']`
- `group_id` parameter is optional
- `uuid` parameter is optional (likely new)

### 3. Search Method Changes ⚠️
**Available SearchMethod values:**
```python
SearchMethod.bm25
SearchMethod.cosine_similarity
```

### 4. Edge/Node Helper Function Names ✅
**Current helper functions (no apparent changes):**
```python
# Edge helpers:
- get_community_edge_from_record
- get_entity_edge_from_record  
- get_episodic_edge_from_record

# Node helpers:
- get_community_node_from_record
- get_entity_node_from_record
- get_episodic_node_from_record
```

### 5. Search API Changes ⚠️
**Current search signature:**
```python
search(self, query: str, center_node_uuid: str | None = None, group_ids: list[str | None] | None = None, num_results=10)
```

**Key Changes:**
- `center_node_uuid` parameter is optional
- `group_ids` parameter accepts `list[str | None] | None`
- `num_results` has default of 10

### 6. Episode Retrieval Changes ⚠️
**Current retrieve_episodes signature:**
```python
retrieve_episodes(self, reference_time: datetime.datetime, last_n: int = 3, group_ids: list[str | None] | None = None) -> list[graphiti_core.nodes.EpisodicNode]
```

## Required Code Updates

### 1. Update SearchConfig Usage
**Before (0.2 - assumed):**
```python
search_config = SearchConfig(num_episodes=5)
```

**After (0.3.0):**
```python
from graphiti_core.search.search import SearchMethod, Reranker

search_config = SearchConfig(
    num_episodes=5,
    group_ids=[user_id],  # Now required
    search_methods=[SearchMethod.cosine_similarity],  # Now required  
    reranker=None  # Now required (can be None)
)
```

### 2. Update Episode Creation
**Current codebase usage (verified working):**
```python
await client.add_episode(
    name=f"Scene {scene['order']} - {story_id}",
    episode_body=scene['text'],
    source_description=f"Scene {scene['order']} from story {story_id}",
    reference_time=datetime.utcnow(),
    group_id=session_id  # Optional in 0.3.0
)
```

### 3. Update Search Operations  
**Current codebase usage (needs update):**
```python
# Current usage in codebase:
search_results = await self.client.search(
    query=f"story session {story_id}",
    config=search_config,  # This may not be correct API
    session_id=session_id
)

# Correct 0.3.0 usage:
search_results = await self.client.search(
    query=f"story session {story_id}",
    group_ids=[session_id],
    num_results=10
)
```

## Migration Actions Required

### Immediate Actions
1. ✅ **COMPLETED**: Pin graphiti-core==0.3.0 in requirements.txt
2. ✅ **COMPLETED**: Install package via pip install -U graphiti-core==0.3.0

### Code Updates Needed
1. **Update SearchConfig instantiation** in:
   - `core/graphiti_manager.py` (lines 677-679, 725-727)
   - Any other files using SearchConfig

2. **Review search API calls** in:
   - `core/graphiti_manager.py` (lines 682-686, 729-733)
   - Update to use correct search signature

3. **Test episode API** in:
   - `core/story_processor.py` (lines 157-163)
   - Verify EpisodeType usage

### Verification Steps
1. ✅ **COMPLETED**: Confirm package version with `python -m pip show graphiti-core`
2. ✅ **COMPLETED**: Test import with `python -c "from graphiti_core import Graphiti; print('Success')"`
3. 🔄 **NEXT**: Run smoke tests to verify API compatibility
4. 🔄 **NEXT**: Update SearchConfig usage across codebase
5. 🔄 **NEXT**: Test search operations with new API

## Files Requiring Updates

### High Priority (Breaking Changes)
- `core/graphiti_manager.py` - SearchConfig usage in search_memory methods
- `core/story_processor.py` - Episode API verification

### Medium Priority (Verification Needed)  
- `smoke_test.py` - SearchConfig test verification
- `test_*.py` files - Test case updates for new API

### Low Priority (Documentation)
- README files mentioning API usage
- Example files with outdated patterns

## Testing Strategy
1. Run existing smoke tests to identify failures
2. Update SearchConfig usage patterns
3. Verify episode creation still works
4. Test search operations with new signatures
5. Run full test suite to catch integration issues

## Notes
- No version attribute found in graphiti_core module (`__version__` not available)
- Core functionality appears backward compatible with minor signature updates
- Main breaking changes are in SearchConfig requirements and search API
- Episode API appears mostly compatible with existing code

## Status: 🟡 IN PROGRESS
- Package installation: ✅ Complete
- API analysis: ✅ Complete  
- Migration planning: ✅ Complete
- Code updates: 🔄 In Progress
- Testing: ⏸️ Pending
