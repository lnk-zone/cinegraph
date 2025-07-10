"""Graph query utilities used by CineGraphAgent."""
from __future__ import annotations

import json
import hashlib
from typing import Dict, Any, List, Tuple
from datetime import datetime


class GraphQueryTools:
    """Encapsulates methods for executing and validating graph queries."""

    # These mixin methods expect the following attributes to be defined on ``self``:
    # ``graphiti_manager``, ``schema_context``, ``query_cache``, ``query_templates``
    # and ``dangerous_operations``.

    # --- template creation -------------------------------------------------
    def _build_query_templates(self) -> Dict[str, str]:
        """Build reusable Cypher query templates."""
        return {
            "character_knowledge_at_time": """
                MATCH (c:Character {name: $character_name, story_id: $story_id})-[knows:KNOWS]->(k:Knowledge)
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                AND k.valid_from <= $timestamp
                AND (k.valid_to IS NULL OR k.valid_to >= $timestamp)
                RETURN k, knows.learned_at, knows.confidence_level, knows.emotional_impact
                ORDER BY k.valid_from DESC
            """,
            "characters_in_scene": """
                MATCH (c:Character)-[present:PRESENT_IN]->(s:Scene {scene_id: $scene_id, story_id: $story_id})
                WHERE ($user_id IS NULL OR c.user_id = $user_id)
                RETURN c, present.participation_level, present.dialogue_count, present.character_state
                ORDER BY c.name
            """,
        }

    # --- query helpers -----------------------------------------------------
    def _generate_query_hash(self, cypher_query: str, params: dict) -> str:
        query_string = f"{cypher_query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(query_string.encode()).hexdigest()

    async def _try_episodic_translation(self, cypher_query: str, params: dict) -> dict | None:
        """Translate common Cypher queries to episodic API calls."""
        try:
            query_upper = cypher_query.upper()
            story_id = params.get("story_id")

            if "COUNT(" in query_upper and "RETURN" in query_upper:
                stats = await self.graphiti_manager.get_query_statistics()
                return {
                    "success": True,
                    "data": [stats],
                    "translated_from": "cypher_count",
                    "api_used": "get_query_statistics",
                    "note": "Translated COUNT query to episodic statistics API",
                }

            if "CONTAINS" in query_upper or "LIKE" in query_upper:
                if story_id:
                    session_id = self.graphiti_manager._story_sessions.get(story_id)
                    if session_id:
                        search_term = self._extract_search_term(cypher_query)
                        if search_term:
                            search_results = await self.graphiti_manager.client.search(
                                query=search_term,
                                group_ids=[session_id],
                                num_results=50,
                            )
                            return {
                                "success": True,
                                "data": search_results,
                                "translated_from": "cypher_content_search",
                                "api_used": "search",
                                "search_term": search_term,
                                "note": "Translated content search query to episodic search API",
                            }

            if any(t in query_upper for t in ["CREATED_AT", "VALID_FROM", "ORDER BY"]):
                if story_id:
                    session_id = self.graphiti_manager._story_sessions.get(story_id)
                    if session_id:
                        episodes = await self.graphiti_manager.client.retrieve_episodes(
                            reference_time=datetime.utcnow(),
                            last_n=20,
                            group_ids=[session_id],
                        )
                        return {
                            "success": True,
                            "data": episodes,
                            "translated_from": "cypher_temporal",
                            "api_used": "retrieve_episodes",
                            "note": "Translated temporal query to episodic retrieve_episodes API",
                        }

            return None
        except Exception:
            return None

    def _extract_search_term(self, cypher_query: str) -> str:
        import re
        match = re.search(r"CONTAINS\s+['\"]([^'\"]+)['\"]|LIKE\s+['\"]%?([^'\"]+)%?['\"]", cypher_query, re.IGNORECASE)
        if match:
            return match.group(1) or match.group(2)
        return "*"

    def get_query_suggestions(self, query: str) -> List[str]:
        suggestions: List[str] = []
        try:
            query_upper = query.upper()
            if "CHARACTER" in query_upper and "KNOWS" in query_upper:
                suggestions.append(
                    "Consider using 'character_knowledge_at_time' template for character knowledge queries"
                )
            if "RELATIONSHIP" in query_upper and "CHARACTER" in query_upper:
                suggestions.append(
                    "Consider using 'character_relationships_detailed' template for relationship analysis"
                )
            if "CONTRADICTS" in query_upper:
                suggestions.append(
                    "Consider using 'contradictions_by_severity' template for contradiction analysis"
                )
            if "STORY_ID" not in query_upper:
                suggestions.append("Add story_id filter for better performance and data isolation")
            if "USER_ID" not in query_upper:
                suggestions.append("Add user_id filter for proper data isolation")
            if "ORDER BY" in query_upper:
                suggestions.append("Consider adding appropriate indexes for ORDER BY clauses")
            if "VALID_FROM" in query_upper or "VALID_TO" in query_upper:
                suggestions.append("Use temporal indexes for better performance on temporal queries")
            if any(enum_name.upper() in query_upper for enum_name in self.schema_context.get("enums", {})):
                suggestions.append("Use enum constraints to improve query performance")
        except Exception as e:
            suggestions.append(f"Error generating suggestions: {e}")
        return suggestions

    def _get_query_suggestions(self, query: str) -> List[str]:
        return self.get_query_suggestions(query)

    # --- validation --------------------------------------------------------
    async def validate_cypher_query(self, cypher_query: str) -> Tuple[bool, str]:
        try:
            query_upper = cypher_query.upper()
            for op in self.dangerous_operations:
                if op in query_upper:
                    return False, f"Dangerous operation '{op}' detected. Only read operations are allowed."

            if "STORY_ID" not in query_upper and "$STORY_ID" not in query_upper:
                return False, "Query must include story_id filter for data isolation"

            if not self._validate_cypher_syntax(cypher_query):
                return False, "Invalid Cypher syntax detected"

            if "VALID_FROM" in query_upper or "VALID_TO" in query_upper:
                if not self._validate_temporal_query_pattern(cypher_query):
                    return False, "Invalid temporal query pattern. Use proper temporal constraints."

            enum_errors = self._validate_enum_usage_in_query(cypher_query)
            if enum_errors:
                return False, f"Enum validation errors: {'; '.join(enum_errors)}"
            return True, "Query validation passed"
        except Exception as e:
            return False, f"Query validation error: {e}"

    def _validate_cypher_syntax(self, query: str) -> bool:
        try:
            paren = bracket = brace = 0
            for ch in query:
                if ch == "(":
                    paren += 1
                elif ch == ")":
                    paren -= 1
                elif ch == "[":
                    bracket += 1
                elif ch == "]":
                    bracket -= 1
                elif ch == "{":
                    brace += 1
                elif ch == "}":
                    brace -= 1
                if paren < 0 or bracket < 0 or brace < 0:
                    return False
            if paren != 0 or bracket != 0 or brace != 0:
                return False
            query_upper = query.upper()
            return "MATCH" in query_upper and "RETURN" in query_upper
        except Exception:
            return False

    def _validate_temporal_query_pattern(self, query: str) -> bool:
        try:
            q = query.lower()
            if "valid_from" in q and not any(op in q for op in ["<=", ">=", "<", ">", "="]):
                return False
            if "valid_to" in q and "is null" not in q and "is not null" not in q:
                return False
            return True
        except Exception:
            return False

    def _validate_enum_usage_in_query(self, query: str) -> List[str]:
        errors: List[str] = []
        try:
            import re
            literals = re.findall(r"'([^']+)'", query) + re.findall(r'"([^\"]+)"', query)
            for enum_name, values in self.schema_context.get("enums", {}).items():
                for literal in literals:
                    if literal in values:
                        continue
                    elif literal.lower() in [v.lower() for v in values]:
                        errors.append(f"Enum value '{literal}' has incorrect case. Use: {values}")
        except Exception as e:
            errors.append(f"Enum validation error: {e}")
        return errors

    # --- public API --------------------------------------------------------
    async def graph_query(self, cypher_query: str, params: dict | None = None, use_cache: bool = True) -> dict:
        params = params or {}
        translated = await self._try_episodic_translation(cypher_query, params)
        if translated:
            return translated

        is_valid, msg = await self.validate_cypher_query(cypher_query)
        if not is_valid:
            return {"success": False, "error": f"Query validation failed: {msg}", "suggestion": "Consider using episodic APIs: search() or retrieve_episodes()"}

        if use_cache:
            h = self._generate_query_hash(cypher_query, params)
            if h in self.query_cache:
                return {"success": True, "data": self.query_cache[h], "cached": True}

        try:
            result = await self.graphiti_manager._run_cypher_query(cypher_query)
            if use_cache:
                h = self._generate_query_hash(cypher_query, params)
                self.query_cache[h] = result
                if len(self.query_cache) > 100:
                    for k in list(self.query_cache.keys())[:20]:
                        del self.query_cache[k]
            return {"success": True, "data": result, "cached": False, "warning": "Direct Cypher is deprecated. Migrate to episodic APIs."}
        except Exception as e:
            return {"success": False, "error": f"Cypher execution failed: {e}", "suggestion": "Consider using episodic APIs instead of direct Cypher"}

    async def optimized_query(self, template_name: str, params: dict) -> dict:
        if template_name not in self.query_templates:
            return {"success": False, "error": f"Unknown template: {template_name}"}
        template_query = self.query_templates[template_name]
        result = await self.graph_query(template_query, params, use_cache=True)
        return {
            "success": result["success"],
            "data": result.get("data"),
            "template_used": template_name,
            "cached": result.get("cached", False),
            "error": result.get("error"),
        }

    async def validate_query(self, cypher_query: str) -> dict:
        is_valid, message = await self.validate_cypher_query(cypher_query)
        return {
            "valid": is_valid,
            "message": message,
            "suggested_optimizations": self._get_query_suggestions(cypher_query) if is_valid else [],
        }
