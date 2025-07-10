"""
Background Task to Track Relationship Evolution
===================================================

This task scans the story graph to detect new relationship milestones
and tension spikes on a nightly schedule.
"""

from celery import shared_task
from core.models import CharacterRelationshipEvolution, RelationshipMilestone
from core.graphiti_manager import GraphitiManager


graphiti_manager = GraphitiManager()

@shared_task
async def detect_milestones_tension_spikes():
    """Detects new relationship milestones and tension spikes."""
    relations = await graphiti_manager.get_all_relationships()
    
    # Placeholder logic for detecting milestones and spikes
    for relation in relations:
        detect_milestone(relation)
        detect_tension_spike(relation)

async def detect_milestone(relation):
    """Detect new relationship milestones."""
    # Example logic for milestone detection
    if relation.strength_after >= 0.8 and relation.milestone != RelationshipMilestone.ALLIES:
        print(f"New milestone detected for: {relation.from_character_id} -> {relation.to_character_id}")

async def detect_tension_spike(relation):
    """Detect tension spikes in relationships."""
    # Example logic for tension spike detection
    if relation.strength_after < 0.3:
        print(f"Tension spike detected for: {relation.from_character_id} -> {relation.to_character_id}")
