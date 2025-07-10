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
    
    async def detect_contradictions(self, story_id: str, user_id: str = None) -> ContradictionDetectionResult:
        """
        Run contradiction detection using episodic memory APIs instead of direct Cypher.
        This implementation uses search and retrieve_episodes to find potential contradictions.
        
        Args:
            story_id: Story identifier to scope the detection
            user_id: Optional user ID for additional filtering
        
        Returns:
            ContradictionDetectionResult object
        """
        start_time = time.time()
        all_contradictions = []
        
        try:
            # Get story session for episodic memory access
            from core.graphiti_manager import GraphitiManager
            graphiti_manager = GraphitiManager()
            await graphiti_manager.initialize()
            
            session_id = graphiti_manager._story_sessions.get(story_id)
            if not session_id:
                print(f"No session found for story {story_id}, returning empty result")
                return ContradictionDetectionResult(
                    story_id=story_id,
                    contradictions_found=[],
                    total_contradictions=0,
                    severity_breakdown={},
                    scan_duration=time.time() - start_time
                )
            
            # Use episodic APIs to find potential contradictions
            # Search for contradictory terms
            contradiction_terms = ["dead", "alive", "enemy", "friend", "not", "never", "always"]
            
            for term in contradiction_terms:
                try:
                    search_results = await self.graphiti.search(
                        query=term,
                        group_ids=[session_id],
                        num_results=50
                    )
                    
                    # Analyze search results for contradictions
                    contradictions = await self._analyze_episodic_contradictions(
                        search_results, story_id, term
                    )
                    all_contradictions.extend(contradictions)
                    
                except Exception as e:
                    print(f"Error searching for term '{term}' in story {story_id}: {str(e)}")
                    continue
            
            # Also retrieve recent episodes for temporal analysis
            try:
                recent_episodes = await self.graphiti.retrieve_episodes(
                    reference_time=datetime.now(),
                    last_n=100,
                    group_ids=[session_id]
                )
                
                # Analyze episodes for temporal contradictions
                temporal_contradictions = await self._analyze_temporal_contradictions(
                    recent_episodes, story_id
                )
                all_contradictions.extend(temporal_contradictions)
                
            except Exception as e:
                print(f"Error retrieving episodes for story {story_id}: {str(e)}")
            
        except Exception as e:
            print(f"Error in episodic contradiction detection for story {story_id}: {str(e)}")
        
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
                    rule_name="episodic_detection"
                ) for c in all_contradictions
            ],
            total_contradictions=len(all_contradictions),
            severity_breakdown=severity_breakdown,
            scan_duration=duration
        )
    
    async def _analyze_episodic_contradictions(self, search_results, story_id: str, search_term: str) -> List[ContradictionMatch]:
        """
        Analyze search results for potential contradictions using episodic data.
        
        Args:
            search_results: Results from episodic search API
            story_id: Story identifier
            search_term: The term that was searched for
        
        Returns:
            List of ContradictionMatch objects
        """
        contradictions = []
        
        try:
            # Group results by similar content to find contradictions
            content_groups = {}
            for result in search_results:
                content = getattr(result, 'episode_body', getattr(result, 'fact', ''))
                if not content:
                    continue
                
                # Simple contradiction detection based on content
                if search_term in ["dead", "alive"]:
                    if "dead" in content.lower() and "alive" in content.lower():
                        contradictions.append(ContradictionMatch(
                            from_knowledge_id=getattr(result, 'uuid', f"episode_{len(contradictions)}"),
                            to_knowledge_id=getattr(result, 'uuid', f"episode_{len(contradictions)}_alt"),
                            severity="critical",
                            reason=f"Character state contradiction detected: {content[:100]}...",
                            detected_at=datetime.now(),
                            confidence=0.9
                        ))
                
                elif search_term in ["enemy", "friend"]:
                    if "enemy" in content.lower() and "friend" in content.lower():
                        contradictions.append(ContradictionMatch(
                            from_knowledge_id=getattr(result, 'uuid', f"episode_{len(contradictions)}"),
                            to_knowledge_id=getattr(result, 'uuid', f"episode_{len(contradictions)}_alt"),
                            severity="medium",
                            reason=f"Relationship contradiction detected: {content[:100]}...",
                            detected_at=datetime.now(),
                            confidence=0.7
                        ))
                
                # Store content for cross-referencing
                if search_term not in content_groups:
                    content_groups[search_term] = []
                content_groups[search_term].append({
                    'content': content,
                    'uuid': getattr(result, 'uuid', ''),
                    'created_at': getattr(result, 'created_at', datetime.now())
                })
            
        except Exception as e:
            print(f"Error analyzing episodic contradictions for term '{search_term}': {str(e)}")
        
        return contradictions
    
    async def _analyze_temporal_contradictions(self, episodes, story_id: str) -> List[ContradictionMatch]:
        """
        Analyze episodes for temporal contradictions using episodic data.
        
        Args:
            episodes: List of episodes from retrieve_episodes API
            story_id: Story identifier
        
        Returns:
            List of ContradictionMatch objects
        """
        contradictions = []
        
        try:
            # Sort episodes by creation time
            sorted_episodes = sorted(
                episodes, 
                key=lambda ep: getattr(ep, 'created_at', datetime.min)
            )
            
            # Look for temporal inconsistencies
            for i, episode in enumerate(sorted_episodes):
                content = getattr(episode, 'episode_body', '')
                episode_time = getattr(episode, 'created_at', datetime.now())
                
                # Check against later episodes for contradictions
                for j in range(i + 1, min(i + 5, len(sorted_episodes))):
                    later_episode = sorted_episodes[j]
                    later_content = getattr(later_episode, 'episode_body', '')
                    later_time = getattr(later_episode, 'created_at', datetime.now())
                    
                    # Simple temporal contradiction detection
                    if self._detect_content_contradiction(content, later_content):
                        contradictions.append(ContradictionMatch(
                            from_knowledge_id=getattr(episode, 'uuid', f"temp_{i}"),
                            to_knowledge_id=getattr(later_episode, 'uuid', f"temp_{j}"),
                            severity="medium",
                            reason=f"Temporal contradiction between episodes at {episode_time} and {later_time}",
                            detected_at=datetime.now(),
                            confidence=0.6
                        ))
            
        except Exception as e:
            print(f"Error analyzing temporal contradictions: {str(e)}")
        
        return contradictions
    
    def _detect_content_contradiction(self, content1: str, content2: str) -> bool:
        """
        Simple content contradiction detection.
        
        Args:
            content1: First piece of content
            content2: Second piece of content
        
        Returns:
            True if contradiction detected, False otherwise
        """
        content1_lower = content1.lower()
        content2_lower = content2.lower()
        
        # Check for obvious contradictions
        contradiction_pairs = [
            ("dead", "alive"),
            ("enemy", "friend"),
            ("married", "single"),
            ("rich", "poor"),
            ("young", "old")
        ]
        
        for term1, term2 in contradiction_pairs:
            if (term1 in content1_lower and term2 in content2_lower) or \
               (term2 in content1_lower and term1 in content2_lower):
                return True
        
        return False
    
    async def create_contradiction_edges(self, contradictions: List[ContradictionMatch], story_id: str):
        """
        Create contradiction records using episodic memory instead of direct edge creation.
        This stores contradiction information as episodes rather than direct graph edges.
        
        Args:
            contradictions: List of ContradictionMatch objects to record
            story_id: Story identifier to include in episode metadata
        """
        try:
            # Get GraphitiManager instance for episodic API access
            from core.graphiti_manager import GraphitiManager
            graphiti_manager = GraphitiManager()
            await graphiti_manager.initialize()
            
            session_id = graphiti_manager._story_sessions.get(story_id)
            if not session_id:
                session_id = await graphiti_manager.create_story_session(story_id)
            
            for contradiction in contradictions:
                # Create episode describing the contradiction
                contradiction_content = f"""
                CONTRADICTION DETECTED:
                From: {contradiction.from_knowledge_id}
                To: {contradiction.to_knowledge_id}
                Severity: {contradiction.severity}
                Reason: {contradiction.reason}
                Confidence: {contradiction.confidence}
                Detected At: {contradiction.detected_at.isoformat()}
                Story ID: {story_id}
                """
                
                try:
                    # Use add_episode to store contradiction information
                    episode_result = await self.graphiti.add_episode(
                        name=f"Contradiction: {contradiction.from_knowledge_id} <-> {contradiction.to_knowledge_id}",
                        episode_body=contradiction_content,
                        source_description=f"Contradiction detection for story {story_id}",
                        reference_time=contradiction.detected_at,
                        group_id=session_id
                    )
                    
                    print(f"Recorded contradiction as episode: {contradiction.from_knowledge_id} <-> {contradiction.to_knowledge_id}")
                    
                except Exception as e:
                    print(f"Error recording contradiction as episode: {str(e)}")
                    
        except Exception as e:
            print(f"Error in episodic contradiction recording: {str(e)}")
    
    async def run_consistency_scan(self, story_id: str, user_id: str = None) -> ContradictionDetectionResult:
        """
        Run a full consistency scan using episodic APIs to detect and record contradictions.
        
        This is the main method called by the background job.
        
        Args:
            story_id: Story identifier to scan
            user_id: Optional user ID for additional filtering
        
        Returns:
            ContradictionDetectionResult with findings
        """
        print(f"Starting episodic consistency scan for story {story_id}...")
        
        # Detect contradictions using episodic APIs
        result = await self.detect_contradictions(story_id, user_id)
        
        if result.contradictions_found:
            print(f"Found {len(result.contradictions_found)} contradictions using episodic APIs")
            print(f"Contradiction summary: {result.severity_breakdown}")
        else:
            print("No contradictions detected via episodic analysis")
        
        return result
    
    async def get_contradiction_report(self, story_id: str = None) -> Dict[str, Any]:
        """
        Generate a comprehensive contradiction report using episodic APIs.
        Searches for contradiction episodes instead of querying CONTRADICTS edges.
        
        Args:
            story_id: Optional story ID to filter contradictions
        
        Returns:
            Dictionary containing contradiction statistics and details
        """
        try:
            # Get GraphitiManager instance for episodic API access
            from core.graphiti_manager import GraphitiManager
            graphiti_manager = GraphitiManager()
            await graphiti_manager.initialize()
            
            # Search for contradiction episodes
            session_ids = []
            if story_id and story_id in graphiti_manager._story_sessions:
                session_ids = [graphiti_manager._story_sessions[story_id]]
            else:
                session_ids = list(graphiti_manager._story_sessions.values())
            
            if not session_ids:
                return {
                    'total_contradictions': 0,
                    'contradictions_by_severity': {},
                    'severity_counts': {},
                    'generated_at': datetime.now().isoformat(),
                    'note': 'No active sessions found for contradiction analysis'
                }
            
            # Search for contradiction episodes
            contradiction_results = await self.graphiti.search(
                query="CONTRADICTION DETECTED",
                group_ids=session_ids,
                num_results=100
            )
            
            # Process results
            contradictions_by_severity = {}
            total_contradictions = len(contradiction_results)
            
            for result in contradiction_results:
                content = getattr(result, 'episode_body', '')
                created_at = getattr(result, 'created_at', datetime.now())
                
                # Parse severity from content
                severity = 'medium'  # default
                if 'Severity: critical' in content:
                    severity = 'critical'
                elif 'Severity: high' in content:
                    severity = 'high'
                elif 'Severity: low' in content:
                    severity = 'low'
                
                if severity not in contradictions_by_severity:
                    contradictions_by_severity[severity] = []
                
                # Extract contradiction details from content
                lines = content.split('\n')
                from_id = 'unknown'
                to_id = 'unknown'
                reason = 'Contradiction detected via episodic analysis'
                confidence = 0.5
                
                for line in lines:
                    if 'From:' in line:
                        from_id = line.split('From:')[1].strip()
                    elif 'To:' in line:
                        to_id = line.split('To:')[1].strip()
                    elif 'Reason:' in line:
                        reason = line.split('Reason:')[1].strip()
                    elif 'Confidence:' in line:
                        try:
                            confidence = float(line.split('Confidence:')[1].strip())
                        except:
                            confidence = 0.5
                
                contradictions_by_severity[severity].append({
                    'from_id': from_id,
                    'to_id': to_id,
                    'reason': reason,
                    'confidence': confidence,
                    'detected_at': created_at.isoformat(),
                    'episode_uuid': getattr(result, 'uuid', '')
                })
            
            return {
                'total_contradictions': total_contradictions,
                'contradictions_by_severity': contradictions_by_severity,
                'severity_counts': {k: len(v) for k, v in contradictions_by_severity.items()},
                'generated_at': datetime.now().isoformat(),
                'note': 'Contradiction report generated from episodic memory search',
                'api_method_used': 'search',
                'sessions_analyzed': len(session_ids)
            }
            
        except Exception as e:
            print(f"Error generating episodic contradiction report: {str(e)}")
            return {
                'error': str(e),
                'generated_at': datetime.now().isoformat(),
                'note': 'Error occurred during episodic contradiction analysis'
            }
