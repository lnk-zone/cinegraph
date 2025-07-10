"""
Tasks Package for CineGraph Background Processing
================================================

This package contains all background tasks for the CineGraph application,
including temporal contradiction detection and story processing.
"""

from .temporal_contradiction_detection import (
    scan_active_stories,
    scan_story_contradictions,
    cleanup_old_contradictions
)
from .relationship_evolution_tracker import (
    detect_milestones_tension_spikes
)
from .continuity_validator import (
    ensure_foreshadow_resolution
)

__all__ = [
    'scan_active_stories',
    'scan_story_contradictions', 
    'cleanup_old_contradictions',
    'detect_milestones_tension_spikes',
    'ensure_foreshadow_resolution'
]
