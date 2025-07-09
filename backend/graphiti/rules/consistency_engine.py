"""
Consistency Engine
==================

This module implements Cypher-based consistency rules and provides
a background job for detecting contradictions in the knowledge graph.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from graphiti_core import Graphiti
from dataclasses import dataclass

# Import the models we need
from core.models import ContradictionEdge, ContradictionDetectionResult, ContradictionSeverity


@dataclass
class ContradictionMatch:
    """Represents a detected contradiction between two knowledge nodes"""
    from_knowledge_id: str
    to_knowledge_id: str
    severity: str
    reason: str
    detected_at: datetime
    confidence: float


class ConsistencyEngine:
    """
    Consistency engine that uses Cypher queries to detect contradictions
    and maintain graph consistency.
    """
    
    def __init__(self, graphiti: Graphiti):
        self.graphiti = graphiti
        self.cypher_rules = {}
        self._setup_cypher_rules()
    
    def _setup_cypher_rules(self):
        """Setup Cypher-based consistency rules"""
        self.cypher_rules = {
            'detect_temporal_contradictions': self._get_temporal_contradiction_query(),
            'detect_relationship_contradictions': self._get_relationship_contradiction_query(),
            'detect_location_contradictions': self._get_location_contradiction_query(),
            'detect_character_state_contradictions': self._get_character_state_contradiction_query(),
            'find_unlinked_contradictions': self._get_unlinked_contradictions_query()
        }
    
    def _get_temporal_contradiction_query(self) -> str:
        """
        Cypher query to detect temporal contradictions in knowledge.
        
        Finds cases where:
        - A character knows something before it was created
        - Events happen in impossible temporal order
        """
        return """
        MATCH (c:Character)-[:KNOWS]->(k1:Knowledge)
        MATCH (c)-[:KNOWS]->(k2:Knowledge)
        WHERE k1.knowledge_id <> k2.knowledge_id
        AND k1.story_id = $story_id
        AND k2.story_id = $story_id
        AND k1.valid_from > k2.valid_to
        AND k1.content CONTAINS k2.content
        AND NOT EXISTS((k1)-[:CONTRADICTS]->(k2))
        AND NOT EXISTS((k2)-[:CONTRADICTS]->(k1))
        RETURN k1.knowledge_id as from_id, k2.knowledge_id as to_id, 
               'temporal' as severity, 
               'Knowledge timeline contradiction' as reason,
               0.8 as confidence
        """
    
    def _get_relationship_contradiction_query(self) -> str:
        """
        Cypher query to detect contradictions in character relationships.
        
        Finds cases where:
        - Characters have conflicting relationship states
        - Mutual relationships are inconsistent
        """
        return """
        MATCH (c1:Character)-[r1:RELATIONSHIP]->(c2:Character)
        MATCH (c1)-[r2:RELATIONSHIP]->(c2)
        WHERE r1.relationship_type <> r2.relationship_type
        AND r1.created_at < r2.created_at
        AND c1.story_id = $story_id
        AND c2.story_id = $story_id
        AND NOT EXISTS((c1)-[:CONTRADICTS]-(c2))
        RETURN c1.character_id + '_' + r1.relationship_type as from_id,
               c1.character_id + '_' + r2.relationship_type as to_id,
               'medium' as severity,
               'Conflicting relationship types' as reason,
               0.9 as confidence
        """
    
    def _get_location_contradiction_query(self) -> str:
        """
        Cypher query to detect location contradictions.
        
        Finds cases where:
        - Characters appear in multiple locations simultaneously
        - Scene locations are inconsistent
        """
        return """
        MATCH (c:Character)-[:PRESENT_IN]->(s1:Scene)-[:OCCURS_IN]->(l1:Location)
        MATCH (c)-[:PRESENT_IN]->(s2:Scene)-[:OCCURS_IN]->(l2:Location)
        WHERE s1.scene_order = s2.scene_order
        AND l1.location_id <> l2.location_id
        AND s1.story_id = $story_id
        AND s2.story_id = $story_id
        AND NOT EXISTS((s1)-[:CONTRADICTS]-(s2))
        RETURN s1.scene_id as from_id, s2.scene_id as to_id,
               'high' as severity,
               'Character in multiple locations simultaneously' as reason,
               0.95 as confidence
        """
    
    def _get_character_state_contradiction_query(self) -> str:
        """
        Cypher query to detect character state contradictions.
        
        Finds cases where:
        - Character knowledge implies contradictory states
        - Character abilities/attributes are inconsistent
        """
        return """
        MATCH (c:Character)-[:KNOWS]->(k1:Knowledge)
        MATCH (c)-[:KNOWS]->(k2:Knowledge)
        WHERE k1.knowledge_id <> k2.knowledge_id
        AND k1.story_id = $story_id
        AND k2.story_id = $story_id
        AND k1.content CONTAINS 'dead' 
        AND k2.content CONTAINS 'alive'
        AND abs(duration.between(k1.valid_from, k2.valid_from).seconds) < 3600
        AND NOT EXISTS((k1)-[:CONTRADICTS]->(k2))
        RETURN k1.knowledge_id as from_id, k2.knowledge_id as to_id,
               'critical' as severity,
               'Character state contradiction (dead/alive)' as reason,
               0.99 as confidence
        """
    
    def _get_unlinked_contradictions_query(self) -> str:
        """
        Cypher query to find all unlinked contradictions.
        
        This is used by the background job to find contradictions
        that haven't been marked with CONTRADICTS edges yet.
        """
        return """
        MATCH (k1:Knowledge), (k2:Knowledge)
        WHERE k1.knowledge_id <> k2.knowledge_id
        AND k1.story_id = $story_id
        AND k2.story_id = $story_id
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
        """
    
    async def detect_contradictions(self, story_id: str) -> ContradictionDetectionResult:
        """
        Run all contradiction detection rules and return found contradictions.
        This is scoped to a specific story_id.
        
        Returns:
            ContradictionDetectionResult object
        """
        start_time = time.time()
        all_contradictions = []
        
        for rule_name, query in self.cypher_rules.items():
            try:
                print(f"Running rule: {rule_name} for story {story_id}")
                params = {"story_id": story_id}
                results = await self.graphiti.execute_cypher(query, params)
                
                for result in results:
                    contradiction = ContradictionMatch(
                        from_knowledge_id=result['from_id'],
                        to_knowledge_id=result['to_id'],
                        severity=result['severity'],
                        reason=result['reason'],
                        detected_at=datetime.now(),
                        confidence=result['confidence']
                    )
                    all_contradictions.append(contradiction)
                    
            except Exception as e:
                print(f"Error running rule {rule_name} for story {story_id}: {str(e)}")
                continue
        
        # Create CONTRADICTS edges
        await self.create_contradiction_edges(all_contradictions, story_id)
        
        # Group contradictions by severity
        severity_breakdown = {}
        for contradiction in all_contradictions:
            severity_breakdown[contradiction.severity] = severity_breakdown.get(contradiction.severity, 0) + 1
        
        duration = time.time() - start_time
        
        return ContradictionDetectionResult(
            story_id=story_id,
            contradictions_found=[
                ContradictionEdge(
                    from_knowledge_id=c.from_knowledge_id,
                    to_knowledge_id=c.to_knowledge_id,
                    severity=ContradictionSeverity(c.severity),
                    reason=c.reason,
                    confidence=c.confidence,
                    detected_at=c.detected_at,
                    story_id=story_id,
                    rule_name="temporal_detection"
                ) for c in all_contradictions
            ],
            total_contradictions=len(all_contradictions),
            severity_breakdown=severity_breakdown,
            scan_duration=duration
        )
    
    async def create_contradiction_edges(self, contradictions: List[ContradictionMatch], story_id: str):
        """
        Create CONTRADICTS edges for detected contradictions.
        
        Args:
            contradictions: List of ContradictionMatch objects to create edges for
            story_id: Story identifier to include in edge properties
        """
        for contradiction in contradictions:
            properties = {
                'severity': contradiction.severity,
                'reason': contradiction.reason,
                'confidence': contradiction.confidence,
                'detected_at': contradiction.detected_at.isoformat(),
                'story_id': story_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            try:
                await self.graphiti.create_edge(
                    "CONTRADICTS",
                    contradiction.from_knowledge_id,
                    contradiction.to_knowledge_id,
                    properties
                )
                print(f"Created CONTRADICTS edge: {contradiction.from_knowledge_id} -> {contradiction.to_knowledge_id}")
                
            except Exception as e:
                print(f"Error creating CONTRADICTS edge: {str(e)}")
    
    async def run_consistency_scan(self, story_id: str) -> ContradictionDetectionResult:
        """
        Run a full consistency scan to detect and mark contradictions.
        
        This is the main method called by the background job.
        """
        print(f"Starting consistency scan for story {story_id}...")
        
        # Detect contradictions
        result = await self.detect_contradictions(story_id)
        
        if result.contradictions_found:
            print(f"Found {len(result.contradictions_found)} contradictions")
            print(f"Contradiction summary: {result.severity_breakdown}")
        else:
            print("No contradictions detected")
        
        return result
    
    async def get_contradiction_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive contradiction report.
        
        Returns:
            Dictionary containing contradiction statistics and details
        """
        # Query for existing CONTRADICTS edges
        query = """
        MATCH (k1:Knowledge)-[c:CONTRADICTS]->(k2:Knowledge)
        RETURN c.severity as severity, c.reason as reason, 
               c.confidence as confidence, c.detected_at as detected_at,
               k1.knowledge_id as from_id, k2.knowledge_id as to_id
        ORDER BY c.confidence DESC
        """
        
        try:
            results = await self.graphiti.execute_cypher(query)
            
            # Process results
            contradictions_by_severity = {}
            total_contradictions = len(results)
            
            for result in results:
                severity = result['severity']
                if severity not in contradictions_by_severity:
                    contradictions_by_severity[severity] = []
                
                contradictions_by_severity[severity].append({
                    'from_id': result['from_id'],
                    'to_id': result['to_id'],
                    'reason': result['reason'],
                    'confidence': result['confidence'],
                    'detected_at': result['detected_at']
                })
            
            return {
                'total_contradictions': total_contradictions,
                'contradictions_by_severity': contradictions_by_severity,
                'severity_counts': {k: len(v) for k, v in contradictions_by_severity.items()},
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating contradiction report: {str(e)}")
            return {
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
