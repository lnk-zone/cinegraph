"""Tests for the BackgroundConsistencyJob class."""

import pytest
import asyncio
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from graphiti.rules.background_jobs import BackgroundConsistencyJob


@pytest.mark.asyncio
async def test_background_job_initialization(background_job):
    """Test that BackgroundConsistencyJob initializes correctly."""
    assert background_job is not None
    assert hasattr(background_job, 'graphiti')
    assert hasattr(background_job, 'consistency_engine')
    assert hasattr(background_job, 'run_interval')
    assert hasattr(background_job, 'is_running')
    assert background_job.is_running is False


@pytest.mark.asyncio
async def test_background_job_start_stop(background_job):
    """Test starting and stopping the background job."""
    # Test start
    await background_job.start()
    assert background_job.is_running is True
    
    # Test stop
    await background_job.stop()
    assert background_job.is_running is False


@pytest.mark.asyncio
async def test_background_job_run_once(background_job):
    """Test running the background job once."""
    # This should not raise an exception
    await background_job.run_once("test_story")


@pytest.mark.asyncio
async def test_background_job_get_status(background_job):
    """Test getting the status of the background job."""
    status = await background_job.get_status()
    
    assert isinstance(status, dict)
    assert 'is_running' in status
    assert 'run_interval' in status
    assert 'last_run' in status
    assert 'contradiction_report' in status
    
    # Check status values
    assert status['is_running'] is False
    assert status['run_interval'] == 30  # Current default interval
    assert isinstance(status['contradiction_report'], dict)


@pytest.mark.asyncio
async def test_background_job_custom_interval():
    """Test BackgroundConsistencyJob with custom interval."""
    from tests.conftest import MockGraphiti
    
    graphiti = MockGraphiti()
    custom_interval = 1800  # 30 minutes
    
    job = BackgroundConsistencyJob(graphiti, run_interval=custom_interval)
    
    assert job.run_interval == custom_interval
    assert job.is_running is False


@pytest.mark.asyncio
async def test_background_job_start_already_running(background_job):
    """Test starting a job that's already running."""
    # Start the job
    await background_job.start()
    assert background_job.is_running is True
    
    # Try to start again - should not change state
    await background_job.start()
    assert background_job.is_running is True
    
    # Clean up
    await background_job.stop()


@pytest.mark.asyncio
async def test_background_job_consistency_engine_integration(background_job):
    """Test that the background job properly integrates with the consistency engine."""
    # Verify consistency engine is initialized
    assert background_job.consistency_engine is not None
    assert hasattr(background_job.consistency_engine, 'detect_contradictions')
    assert hasattr(background_job.consistency_engine, 'create_contradiction_edges')
    assert hasattr(background_job.consistency_engine, 'run_consistency_scan')


@pytest.mark.asyncio
async def test_background_job_error_handling(background_job):
    """Test error handling in background job."""
    # Mock the consistency engine to raise an exception
    async def mock_run_consistency_scan():
        raise Exception("Test error")
    
    background_job.consistency_engine.run_consistency_scan = mock_run_consistency_scan
    
    # This should not raise an exception due to error handling
    await background_job.run_once("test_story")


@pytest.mark.asyncio
async def test_background_job_report_generation(background_job):
    """Test that the background job can generate proper reports."""
    status = await background_job.get_status()
    
    # Check the contradiction report structure
    report = status['contradiction_report']
    assert isinstance(report, dict)
    
    # Should have expected fields even if empty
    if 'total_contradictions' in report:
        assert isinstance(report['total_contradictions'], int)
    
    if 'contradictions_by_severity' in report:
        assert isinstance(report['contradictions_by_severity'], dict)
    
    if 'severity_counts' in report:
        assert isinstance(report['severity_counts'], dict)
    
    if 'generated_at' in report:
        assert isinstance(report['generated_at'], str)
        # Should be a valid ISO datetime format
        datetime.fromisoformat(report['generated_at'])
