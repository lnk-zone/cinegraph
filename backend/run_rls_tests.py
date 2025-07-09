#!/usr/bin/env python3
"""
Test Runner for RLS End-to-End Tests
===================================

This script runs the RLS end-to-end tests and provides detailed output
about the test results, including:
- User isolation verification
- Authentication and authorization testing
- Rate limiting functionality
- Row Level Security compliance
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime

def run_tests():
    """Run the RLS end-to-end tests"""
    
    print("=" * 80)
    print("🚀 Running RLS End-to-End Tests")
    print("=" * 80)
    print()
    
    # Set up environment
    print("📋 Test Environment Setup:")
    print(f"   Python version: {sys.version}")
    print(f"   Working directory: {os.getcwd()}")
    print(f"   Test timestamp: {datetime.now().isoformat()}")
    print()
    
    # Check if pytest is available
    try:
        import pytest
        print(f"✅ pytest version: {pytest.__version__}")
    except ImportError:
        print("❌ pytest not found. Please install: pip install pytest pytest-asyncio")
        return False
    
    # Check if required dependencies are available
    required_modules = ["httpx", "fastapi", "pytest_asyncio"]
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} available")
        except ImportError:
            missing_modules.append(module)
            print(f"❌ {module} not found")
    
    if missing_modules:
        print(f"\n❌ Missing required modules: {', '.join(missing_modules)}")
        print("Please install with: pip install " + " ".join(missing_modules))
        return False
    
    print()
    
    # Run the simplified RLS tests
    print("🔒 Running RLS Tests...")
    print("-" * 50)
    
    test_files = [
        "test_rls_simplified.py"
    ]
    
    all_passed = True
    
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"❌ Test file not found: {test_file}")
            all_passed = False
            continue
        
        print(f"\n📝 Running {test_file}...")
        
        # Run pytest with verbose output
        cmd = [
            sys.executable, "-m", "pytest", 
            test_file, 
            "-v", 
            "--tb=short", 
            "--no-header",
            "-s"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0:
                print("✅ All tests passed!")
                print(f"Output:\n{result.stdout}")
            else:
                print(f"❌ Some tests failed (exit code: {result.returncode})")
                print(f"Output:\n{result.stdout}")
                if result.stderr:
                    print(f"Errors:\n{result.stderr}")
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print("❌ Tests timed out after 2 minutes")
            all_passed = False
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            all_passed = False
    
    print("\n" + "=" * 80)
    
    if all_passed:
        print("🎉 ALL RLS TESTS PASSED!")
        print()
        print("✅ User isolation is working correctly")
        print("✅ Authentication is properly enforced")
        print("✅ Rate limiting is functional")
        print("✅ Row Level Security is properly implemented")
        print()
        print("The following RLS features were verified:")
        print("  • User A cannot access User B's stories")
        print("  • User A cannot access User B's alerts")
        print("  • Authentication is required for protected endpoints")
        print("  • Rate limiting works with authentication")
        print("  • Story deletion is properly isolated")
        print("  • Character knowledge is user-specific")
        print("  • Profile access is user-specific")
        print("  • Health check is accessible without auth")
    else:
        print("❌ SOME RLS TESTS FAILED!")
        print()
        print("Please review the test output above for details.")
        print("Common issues:")
        print("  • Missing environment variables")
        print("  • Database connection issues")
        print("  • Authentication configuration problems")
        print("  • Missing dependencies")
    
    print("=" * 80)
    return all_passed

def main():
    """Main function"""
    success = run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
