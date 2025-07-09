#!/usr/bin/env python3
"""
Example Usage of Graphiti Rules Engine
======================================

This example demonstrates how to use the Graphiti rules engine to:
1. Set up validation rules and triggers
2. Start background consistency jobs
3. Handle rule violations
4. Generate consistency reports

Usage:
    python examples/rules_usage_example.py
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to import graphiti modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graphiti_core import Graphiti
from graphiti.rules.validation_rules import ValidationRules
from graphiti.rules.consistency_engine import ConsistencyEngine
from graphiti.rules.background_jobs import BackgroundConsistencyJob


async def main():
    """Main example function demonstrating rules engine usage."""
    
    print("=== Graphiti Rules Engine Example ===\n")
    
    # Initialize mock Graphiti instance (for demonstration)
    print("1. Initializing mock Graphiti...")
    
    class MockGraphiti:
        async def initialize(self):
            pass
        
        async def close(self):
            pass
        
        async def register_trigger(self, trigger_name, trigger_type, callback):
            print(f"   Registered trigger: {trigger_name} ({trigger_type})")
        
        async def execute_cypher(self, query):
            return []
        
        async def create_edge(self, edge_type, from_id, to_id, properties):
            print(f"   Would create {edge_type} edge: {from_id} -> {to_id}")
    
    graphiti = MockGraphiti()
    await graphiti.initialize()
    
    # Set up validation rules
    print("2. Setting up validation rules...")
    validation_rules = ValidationRules(graphiti)
    await validation_rules.register_triggers()
    
    # Set up consistency engine
    print("3. Setting up consistency engine...")
    consistency_engine = ConsistencyEngine(graphiti)
    
    # Set up background job
    print("4. Setting up background consistency job...")
    background_job = BackgroundConsistencyJob(graphiti, run_interval=300)  # 5 minutes
    
    # Start background job
    await background_job.start()
    
    # Example 1: Valid edge creation
    print("\n=== Example 1: Valid Edge Creation ===")
    
    valid_from_node = {
        'character_id': 'char_001',
        'name': 'Alice',
        'created_at': '2023-01-01T10:00:00'
    }
    
    valid_to_node = {
        'knowledge_id': 'know_001',
        'content': 'The secret of the castle',
        'valid_from': '2023-01-01T12:00:00'
    }
    
    valid_properties = {
        'created_at': '2023-01-01T12:00:00',
        'updated_at': '2023-01-01T12:00:00'
    }
    
    is_valid, error_msg = await validation_rules.validate_edge_creation(
        "KNOWS", valid_from_node, valid_to_node, valid_properties
    )
    
    print(f"Valid edge creation: {is_valid}")
    if error_msg:
        print(f"Error: {error_msg}")
    
    # Example 2: Invalid edge creation (temporal violation)
    print("\n=== Example 2: Invalid Edge Creation (Temporal Violation) ===")
    
    invalid_from_node = {
        'character_id': 'char_002',
        'name': 'Bob',
        'created_at': '2023-01-01T15:00:00'
    }
    
    invalid_to_node = {
        'knowledge_id': 'know_002',
        'content': 'Old secret',
        'valid_from': '2023-01-01T10:00:00'
    }
    
    invalid_properties = {
        'created_at': '2023-01-01T15:00:00',
        'updated_at': '2023-01-01T15:00:00'
    }
    
    is_valid, error_msg = await validation_rules.validate_edge_creation(
        "KNOWS", invalid_from_node, invalid_to_node, invalid_properties
    )
    
    print(f"Invalid edge creation: {is_valid}")
    if error_msg:
        print(f"Error: {error_msg}")
    
    # Example 3: Self-loop prevention
    print("\n=== Example 3: Self-Loop Prevention ===")
    
    self_loop_node = {
        'character_id': 'char_003',
        'name': 'Charlie'
    }
    
    is_valid, error_msg = await validation_rules.validate_edge_creation(
        "RELATIONSHIP", self_loop_node, self_loop_node, {}
    )
    
    print(f"Self-loop prevention: {is_valid}")
    if error_msg:
        print(f"Error: {error_msg}")
    
    # Example 4: Run consistency scan
    print("\n=== Example 4: Manual Consistency Scan ===")
    
    await consistency_engine.run_consistency_scan()
    
    # Example 5: Get contradiction report
    print("\n=== Example 5: Contradiction Report ===")
    
    report = await consistency_engine.get_contradiction_report()
    print(f"Total contradictions found: {report.get('total_contradictions', 0)}")
    print(f"Severity breakdown: {report.get('severity_counts', {})}")
    
    # Example 6: Background job status
    print("\n=== Example 6: Background Job Status ===")
    
    status = await background_job.get_status()
    print(f"Background job running: {status['is_running']}")
    print(f"Run interval: {status['run_interval']} seconds")
    
    # Example 7: Validation statistics
    print("\n=== Example 7: Validation Statistics ===")
    
    stats = await validation_rules.get_validation_stats()
    print(f"Rules enabled: {stats['rules_enabled']}")
    print(f"Active triggers: {stats['active_triggers']}")
    
    # Example 8: Test all validation rules
    print("\n=== Example 8: Testing All Validation Rules ===")
    
    test_cases = [
        {
            'name': 'Valid KNOWS edge',
            'edge_type': 'KNOWS',
            'from_node': {'character_id': 'c1', 'created_at': '2023-01-01T10:00:00'},
            'to_node': {'knowledge_id': 'k1', 'valid_from': '2023-01-01T11:00:00'},
            'properties': {'created_at': '2023-01-01T11:00:00'}
        },
        {
            'name': 'Invalid KNOWS edge (temporal)',
            'edge_type': 'KNOWS',
            'from_node': {'character_id': 'c2', 'created_at': '2023-01-01T15:00:00'},
            'to_node': {'knowledge_id': 'k2', 'valid_from': '2023-01-01T10:00:00'},
            'properties': {'created_at': '2023-01-01T15:00:00'}
        },
        {
            'name': 'Valid RELATIONSHIP edge',
            'edge_type': 'RELATIONSHIP',
            'from_node': {'character_id': 'c1'},
            'to_node': {'character_id': 'c2'},
            'properties': {}
        },
        {
            'name': 'Invalid RELATIONSHIP edge (self-loop)',
            'edge_type': 'RELATIONSHIP',
            'from_node': {'character_id': 'c1'},
            'to_node': {'character_id': 'c1'},
            'properties': {}
        },
        {
            'name': 'Valid PRESENT_IN edge',
            'edge_type': 'PRESENT_IN',
            'from_node': {'character_id': 'c1'},
            'to_node': {'scene_id': 's1', 'scene_order': 1},
            'properties': {}
        },
        {
            'name': 'Invalid PRESENT_IN edge (negative scene order)',
            'edge_type': 'PRESENT_IN',
            'from_node': {'character_id': 'c1'},
            'to_node': {'scene_id': 's1', 'scene_order': -1},
            'properties': {}
        }
    ]
    
    for test_case in test_cases:
        is_valid, error_msg = await validation_rules.validate_edge_creation(
            test_case['edge_type'],
            test_case['from_node'],
            test_case['to_node'],
            test_case['properties']
        )
        
        status = "✓ PASS" if is_valid else "✗ FAIL"
        print(f"{status} - {test_case['name']}")
        if error_msg:
            print(f"    Error: {error_msg}")
    
    # Stop background job
    print("\n=== Cleanup ===")
    await background_job.stop()
    
    # Close Graphiti connection
    await graphiti.close()
    
    print("\nExample completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
