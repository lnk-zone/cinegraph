from __future__ import annotations

"""Analyze character relationships using a CineGraphAgent."""

from typing import Any, List, Dict


class CharacterRelationshipAnalyzer:
    """Fetch character relationships from the knowledge graph."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def analyze_relationships(self, story_id: str) -> List[Dict[str, Any]]:
        """Return relationships for the given story.

        This queries the knowledge graph via ``graph_query``. Each returned item
        should describe a relationship with ``from_character``, ``to_character``
        and ``relationship_type`` keys.
        """
        query = (
            "MATCH (a:Character)-[r]->(b:Character) "
            "WHERE r.story_id = $story_id "
            "RETURN a.name AS from_character, b.name AS to_character, "
            "type(r) AS relationship_type"
        )
        result = await self.agent.graph_query(query, {"story_id": story_id})
        return result.get("data", [])
