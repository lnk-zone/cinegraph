#!/usr/bin/env python3
"""
Demo Script: Quick Fix Secret Management Implementation
======================================================

This script demonstrates the quick fix implementation for secret management
in the CineGraph project.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and display its output."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def main():
    """Main demo function."""
    print("🚀 CineGraph Quick Fix Secret Management Demo")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("scripts/fix_env_secrets.py").exists():
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Demo 1: Scan for secrets (dry run)
    print("\n📋 Demo 1: Scanning for secrets and environment variables")
    run_command(
        "python3 scripts/fix_env_secrets.py --dry-run --verbose",
        "Scan for secrets without making changes"
    )
    
    # Demo 2: Generate patches
    print("\n📋 Demo 2: Generating reviewable patches")
    run_command(
        "python3 scripts/generate_secret_patches.py",
        "Generate git patches for secret management fixes"
    )
    
    # Demo 3: Show current environment status
    print("\n📋 Demo 3: Current environment variable status")
    env_vars = [
        "OPENAI_API_KEY",
        "SUPABASE_URL", 
        "SUPABASE_SERVICE_ROLE_KEY",
        "GRAPHITI_DATABASE_PASSWORD",
        "REDIS_URL"
    ]
    
    print("\nEnvironment Variable Status:")
    print("-" * 40)
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if len(value) > 8:
                masked = f"{value[:4]}...{value[-4:]}"
            else:
                masked = "***"
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: Not set")
    
    # Demo 4: Show files that would be modified
    print("\n📋 Demo 4: Files in the current implementation")
    files_to_check = [
        "backend/.env.example",
        "backend/setup_enhanced_agent.py", 
        "scripts/fix_env_secrets.py",
        "scripts/generate_secret_patches.py",
        "scripts/README.md",
        "QUICK_FIX_SUMMARY.md"
    ]
    
    print("\nImplementation Files:")
    print("-" * 40)
    for file_path in files_to_check:
        if Path(file_path).exists():
            size = Path(file_path).stat().st_size
            print(f"✅ {file_path} ({size} bytes)")
        else:
            print(f"❌ {file_path}: Missing")
    
    # Demo 5: Show patches directory
    patches_dir = Path("patches")
    if patches_dir.exists():
        print("\n📋 Demo 5: Generated patches")
        print("-" * 40)
        for patch_file in patches_dir.glob("*.patch"):
            print(f"📄 {patch_file}")
    
    # Demo 6: Show git status
    print("\n📋 Demo 6: Git status of changes")
    run_command("git status --porcelain", "Show modified files")
    
    # Demo 7: Show branch information
    print("\n📋 Demo 7: Branch information")
    run_command("git branch", "Show current branch")
    run_command("git log --oneline -5", "Show recent commits")
    
    print("\n" + "="*60)
    print("🎉 Demo completed successfully!")
    print("="*60)
    
    print("\nNext steps:")
    print("1. Review the generated patches in the patches/ directory")
    print("2. Test the scripts with your actual environment variables")
    print("3. Integrate the scripts into your CI/CD pipeline")
    print("4. Set up environment variables according to backend/.env.example")
    
    print("\nUseful commands:")
    print("- Review changes: git diff HEAD~3")
    print("- Apply patches: git apply patches/secret_fix_*.patch")
    print("- Run security scan: python3 scripts/fix_env_secrets.py --dry-run")

if __name__ == "__main__":
    main()
