"""
Temporal Contradiction Detection Task
=====================================

Tasks related to temporal contradiction detection in the knowledge graph.
These tasks are managed by Celery and scheduled periodically.
"""

import asyncio
import json
from celery import shared_task
from core.graphiti_manager import GraphitiManager
from core.models import ContradictionSeverity
from core.redis_alerts import alert_manager
from celery_config import CRITICAL_SEVERITY_THRESHOLD
from graphiti.rules.consistency_engine import ConsistencyEngine

graphiti_manager = GraphitiManager()


@shared_task
async def scan_active_stories():
    """Periodic task to scan active stories for contradictions."""
    active_stories = await graphiti_manager.get_active_stories()

    for story_id in active_stories:
        await scan_story_contradictions(story_id)


@shared_task
async def scan_story_contradictions(story_id: str, user_id: str):
    """Run contradiction detection for a specific story using episodic APIs."""
    await graphiti_manager.initialize()
    
    # Use the updated detect_contradictions method with episodic APIs
    result = await graphiti_manager.detect_contradictions(story_id, user_id)
    
    if result["status"] == "success":
        detection_result = result["result"]
        
        # Publish an alert for critical contradictions
        for contradiction in detection_result.contradictions_found:
            if contradiction.severity.value == CRITICAL_SEVERITY_THRESHOLD:
                alert_data = {
                    'story_id': story_id,
                    'from': contradiction.from_knowledge_id,
                    'to': contradiction.to_knowledge_id,
                    'severity': contradiction.severity.value,
                    'reason': contradiction.reason,
                    'detected_at': contradiction.detected_at.isoformat(),
                    'detection_method': 'episodic_apis',
                    'note': 'Contradiction detected using search and retrieve_episodes APIs'
                }
                alert_manager.publish_alert(alert_data)
        
        return {
            "status": "success",
            "story_id": story_id,
            "contradictions_found": len(detection_result.contradictions_found),
            "critical_contradictions": len([c for c in detection_result.contradictions_found if c.severity.value == CRITICAL_SEVERITY_THRESHOLD]),
            "detection_method": "episodic_apis",
            "note": "Contradiction detection completed using episodic memory APIs"
        }
    else:
        return result


@shared_task
def cleanup_old_contradictions():
    """Routine cleanup task to manage old contradictions."""
    # Placeholder for cleanup logic
    pass
