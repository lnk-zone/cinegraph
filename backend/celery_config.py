"""
Celery Configuration for CineGraph Background Tasks
==================================================

This module configures Celery for background processing tasks including
temporal contradiction detection loops.
"""

import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# Initialize Celery instance
celery_app = Celery(
    'cinegraph_tasks',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    include=[
        'tasks.temporal_contradiction_detection',
        'tasks.story_processing'
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    result_expires=3600,  # 1 hour
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        'temporal-contradiction-detection': {
            'task': 'tasks.temporal_contradiction_detection.scan_active_stories',
            'schedule': 30.0,  # Every 30 seconds
            'options': {'queue': 'contradiction_detection'}
        },
        'cleanup-old-contradictions': {
            'task': 'tasks.temporal_contradiction_detection.cleanup_old_contradictions',
            'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
            'options': {'queue': 'maintenance'}
        }
    },
    task_routes={
        'tasks.temporal_contradiction_detection.*': {'queue': 'contradiction_detection'},
        'tasks.story_processing.*': {'queue': 'story_processing'},
    }
)

# Redis configuration for pub/sub
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Alert channel configuration
ALERTS_CHANNEL = "alerts"
CRITICAL_SEVERITY_THRESHOLD = "critical"
