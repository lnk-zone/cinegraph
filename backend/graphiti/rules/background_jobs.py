"""
Background Consistency Engine
============================

This module implements a background job that scans the Graphiti
knowledge graph for unlinked contradictions and attaches a CONTRADICTS edge
with severity.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
from graphiti_core import Graphiti
from .consistency_engine import ConsistencyEngine


class BackgroundConsistencyJob:
    """
    Background job for consistency validation and contradiction
    detection in the knowledge graph.
    """
    def __init__(self, graphiti: Graphiti, run_interval: int = 30):
        self.graphiti = graphiti
        self.consistency_engine = ConsistencyEngine(graphiti)
        self.run_interval = run_interval  # Default: 30 seconds
        self.is_running = False
    
    async def start(self):
        """
        Start the background consistency job.
        """
        if self.is_running:
            print("Background consistency job is already running")
            return
        
        self.is_running = True
        print(f"Starting background consistency job (interval: {self.run_interval}s)")
        
        # Start the background task
        asyncio.create_task(self._run_loop())
    
    async def stop(self):
        """
        Stop the background consistency job.
        """
        print("Stopping background consistency job")
        self.is_running = False
    
    async def _run_loop(self):
        """
        Main background job loop that runs consistency checks at regular intervals.
        """
        while self.is_running:
            try:
                print(f"Running scheduled consistency check at {datetime.now()}")
                await self.consistency_engine.run_consistency_scan()
                print("Consistency check completed successfully")
                
                # Wait for the next run
                await asyncio.sleep(self.run_interval)
                
            except Exception as e:
                print(f"Error during consistency check: {str(e)}")
                # Wait a bit before retrying
                await asyncio.sleep(min(300, self.run_interval // 12))  # 5 min max
    
    async def run_once(self, story_id: str):
        """
        Run a single consistency check immediately.
        
        This method can be called manually to trigger a consistency check
        without waiting for the scheduled interval.
        """
        try:
            print(f"Running manual consistency check for story {story_id}...")
            result = await self.consistency_engine.run_consistency_scan(story_id)
            print(f"Manual consistency check completed for story {story_id}")
            return result
        except Exception as e:
            print(f"Error during manual consistency check for story {story_id}: {str(e)}")
            return None
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the background job.
        
        Returns:
            Dictionary containing job status and statistics
        """
        contradiction_report = await self.consistency_engine.get_contradiction_report()
        
        return {
            'is_running': self.is_running,
            'run_interval': self.run_interval,
            'last_run': datetime.now().isoformat(),
            'contradiction_report': contradiction_report
        }

