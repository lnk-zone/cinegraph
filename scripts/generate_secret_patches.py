#!/usr/bin/env python3
"""
Generate PR Patches for Secret Management
==========================================

This script generates specific patches to replace hard-coded secrets
with proper environment variable references. It creates git patches
that can be reviewed before applying.

Usage:
    python scripts/generate_secret_patches.py [--apply] [--target-file FILE]
"""

import os
import re
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

@dataclass
class SecretReplacement:
    """Represents a secret replacement operation."""
    file_path: str
    line_number: int
    original_line: str
    replacement_line: str
    secret_pattern: str
    env_var_name: str
    description: str

class SecretPatcher:
    """Generates patches for secret replacements."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backend_root = self.project_root / 'backend'
        
        # Define specific secret patterns and their replacements
        self.secret_replacements = [
            # Hard-coded password in setup_enhanced_agent.py
            {
                'file_pattern': 'setup_enhanced_agent.py',
                'original_pattern': r'password=os\.getenv\("GRAPHITI_DATABASE_PASSWORD", "password"\)',
                'replacement': 'password=os.getenv("GRAPHITI_DATABASE_PASSWORD")',
                'env_var': 'GRAPHITI_DATABASE_PASSWORD',
                'description': 'Remove hard-coded password fallback'
            },
            # Hard-coded password in other files
            {
                'file_pattern': '*.py',
                'original_pattern': r'password=os\.getenv\([^,]+, "password"\)',
                'replacement': 'password=os.getenv("GRAPHITI_DATABASE_PASSWORD")',
                'env_var': 'GRAPHITI_DATABASE_PASSWORD',
                'description': 'Remove hard-coded password fallback'
            },
            # Hard-coded database defaults
            {
                'file_pattern': '*.py',
                'original_pattern': r'database_url=os\.getenv\([^,]+, "bolt://localhost:7687"\)',
                'replacement': 'database_url=os.getenv("GRAPHITI_DATABASE_URL", "bolt://localhost:7687")',
                'env_var': 'GRAPHITI_DATABASE_URL',
                'description': 'Standardize database URL environment variable'
            },
            # Missing environment variable checks
            {
                'file_pattern': '*.py',
                'original_pattern': r'(\s+)if not ([a-z_]+):\s*\n\s+raise ValueError\([^)]+\)\s*',
                'replacement': r'\1if not \2:\n\1    raise ValueError(f"\2 environment variable is required")',
                'env_var': 'VALIDATION',
                'description': 'Improve error messages for missing environment variables'
            }
        ]
        
        # Define environment variable improvements
        self.env_var_improvements = [
            # Add validation for critical variables
            {
                'file_pattern': 'app/auth.py',
                'after_line': 'from jose import JWTError, jwt',
                'insert_code': '''
# Validate required environment variables
required_env_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
''',
                'description': 'Add environment variable validation to auth module'
            },
            # Add validation for GraphitiManager
            {
                'file_pattern': 'core/graphiti_manager.py',
                'after_line': 'from .models import (',
                'insert_code': '''
# Validate critical environment variables
def validate_graphiti_env_vars():
    """Validate that required Graphiti environment variables are set."""
    required_vars = [
        "GRAPHITI_DATABASE_URL",
        "GRAPHITI_DATABASE_USER", 
        "GRAPHITI_DATABASE_PASSWORD"
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required Graphiti environment variables: {', '.join(missing_vars)}")
''',
                'description': 'Add environment variable validation to GraphitiManager'
            }
        ]

    def scan_for_secret_issues(self) -> List[SecretReplacement]:
        """Scan for specific secret management issues."""
        replacements = []
        
        for file_path in self._get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    
                    for replacement_config in self.secret_replacements:
                        if not self._file_matches_pattern(file_path, replacement_config['file_pattern']):
                            continue
                            
                        pattern = replacement_config['original_pattern']
                        replacement = replacement_config['replacement']
                        
                        for line_no, line in enumerate(lines, 1):
                            if re.search(pattern, line):
                                new_line = re.sub(pattern, replacement, line)
                                
                                replacements.append(SecretReplacement(
                                    file_path=str(file_path),
                                    line_number=line_no,
                                    original_line=line,
                                    replacement_line=new_line,
                                    secret_pattern=pattern,
                                    env_var_name=replacement_config['env_var'],
                                    description=replacement_config['description']
                                ))
                                
            except Exception as e:
                print(f"Error scanning {file_path}: {e}")
                
        return replacements

    def generate_patches(self, replacements: List[SecretReplacement]) -> List[str]:
        """Generate git patches for the replacements."""
        patches = []
        
        # Group replacements by file
        replacements_by_file = {}
        for replacement in replacements:
            file_path = replacement.file_path
            if file_path not in replacements_by_file:
                replacements_by_file[file_path] = []
            replacements_by_file[file_path].append(replacement)
        
        # Generate a patch for each file
        for file_path, file_replacements in replacements_by_file.items():
            patch_content = self._generate_file_patch(file_path, file_replacements)
            if patch_content:
                patches.append(patch_content)
                
        return patches

    def apply_replacements(self, replacements: List[SecretReplacement]) -> None:
        """Apply the secret replacements to files."""
        
        # Group by file
        replacements_by_file = {}
        for replacement in replacements:
            file_path = replacement.file_path
            if file_path not in replacements_by_file:
                replacements_by_file[file_path] = []
            replacements_by_file[file_path].append(replacement)
        
        # Apply replacements to each file
        for file_path, file_replacements in replacements_by_file.items():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.splitlines()
                
                # Apply replacements in reverse order to preserve line numbers
                for replacement in reversed(sorted(file_replacements, key=lambda r: r.line_number)):
                    line_idx = replacement.line_number - 1
                    lines[line_idx] = replacement.replacement_line
                
                # Write back
                with open(file_path, 'w') as f:
                    f.write('\n'.join(lines))
                
                print(f"✅ Applied {len(file_replacements)} replacements to {file_path}")
                
            except Exception as e:
                print(f"❌ Error applying replacements to {file_path}: {e}")

    def update_env_example_with_missing_vars(self) -> None:
        """Update .env.example with any missing environment variables."""
        
        env_example_path = self.backend_root / '.env.example'
        
        # Read current .env.example
        current_vars = set()
        if env_example_path.exists():
            with open(env_example_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        var_name = line.split('=')[0].strip()
                        current_vars.add(var_name)
        
        # Define required variables that might be missing
        required_vars = {
            'DATABASE_URL': 'postgresql://user:password@localhost:5432/cinegraph',
            'DB_PASSWORD': 'your_database_password_here',
            'SUPABASE_DB_PASSWORD': 'your_supabase_db_password_here',
            'SECRET_KEY': 'your_secret_key_here',
            'JWT_SECRET_KEY': 'your_jwt_secret_key_here',
            'ENCRYPTION_KEY': 'your_encryption_key_here'
        }
        
        missing_vars = set(required_vars.keys()) - current_vars
        
        if missing_vars:
            with open(env_example_path, 'a') as f:
                f.write('\n# Additional environment variables\n')
                for var in sorted(missing_vars):
                    f.write(f'{var}={required_vars[var]}\n')
            
            print(f"✅ Added {len(missing_vars)} missing variables to .env.example")

    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the backend directory."""
        python_files = []
        for file_path in self.backend_root.rglob('*.py'):
            # Skip test files and __pycache__
            if ('test' in str(file_path) or 
                '__pycache__' in str(file_path) or
                '.git' in str(file_path)):
                continue
            python_files.append(file_path)
        return python_files

    def _file_matches_pattern(self, file_path: Path, pattern: str) -> bool:
        """Check if file matches the given pattern."""
        if pattern == '*.py':
            return file_path.suffix == '.py'
        else:
            return pattern in str(file_path)

    def _generate_file_patch(self, file_path: str, replacements: List[SecretReplacement]) -> Optional[str]:
        """Generate a git patch for a single file."""
        
        try:
            # Read original file
            with open(file_path, 'r') as f:
                original_lines = f.readlines()
            
            # Create modified version
            modified_lines = original_lines.copy()
            
            # Apply replacements in reverse order
            for replacement in reversed(sorted(replacements, key=lambda r: r.line_number)):
                line_idx = replacement.line_number - 1
                modified_lines[line_idx] = replacement.replacement_line + '\n'
            
            # Generate unified diff
            import difflib
            
            diff = difflib.unified_diff(
                original_lines,
                modified_lines,
                fromfile=f'a/{file_path}',
                tofile=f'b/{file_path}',
                lineterm=''
            )
            
            diff_content = '\n'.join(diff)
            
            if diff_content:
                # Add patch header
                patch_header = f"""Subject: [PATCH] Fix hard-coded secrets in {Path(file_path).name}

Replace hard-coded secrets with proper environment variable references:
"""
                for replacement in replacements:
                    patch_header += f"- {replacement.description}\n"
                
                patch_header += "\n" + diff_content
                return patch_header
            
            return None
            
        except Exception as e:
            print(f"Error generating patch for {file_path}: {e}")
            return None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Generate patches for secret management')
    parser.add_argument('--apply', action='store_true', help='Apply the patches directly')
    parser.add_argument('--target-file', help='Target specific file for patching')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    
    args = parser.parse_args()
    
    # Initialize patcher
    patcher = SecretPatcher(args.project_root)
    
    print("🔍 Scanning for secret management issues...")
    
    # Scan for issues
    replacements = patcher.scan_for_secret_issues()
    
    if args.target_file:
        # Filter for specific file
        replacements = [r for r in replacements if args.target_file in r.file_path]
    
    print(f"Found {len(replacements)} secret management issues")
    
    if not replacements:
        print("✅ No secret management issues found!")
        return
    
    # Show what will be changed
    print("\n🔧 Planned changes:")
    for replacement in replacements:
        print(f"  📄 {replacement.file_path}:{replacement.line_number}")
        print(f"    Description: {replacement.description}")
        print(f"    Original: {replacement.original_line.strip()}")
        print(f"    Replacement: {replacement.replacement_line.strip()}")
        print()
    
    if args.apply:
        # Apply changes
        print("🚀 Applying changes...")
        patcher.apply_replacements(replacements)
        patcher.update_env_example_with_missing_vars()
        print("✅ Changes applied successfully!")
    else:
        # Generate patches
        print("📝 Generating patches...")
        patches = patcher.generate_patches(replacements)
        
        # Save patches
        patches_dir = Path(args.project_root) / 'patches'
        patches_dir.mkdir(exist_ok=True)
        
        for i, patch in enumerate(patches):
            patch_file = patches_dir / f'secret_fix_{i+1:03d}.patch'
            with open(patch_file, 'w') as f:
                f.write(patch)
            print(f"  📄 Saved patch: {patch_file}")
        
        print(f"\n✅ Generated {len(patches)} patches in {patches_dir}")
        print("To apply patches, run: git apply patches/secret_fix_*.patch")
        print("Or run this script with --apply to apply changes directly")

if __name__ == '__main__':
    main()
