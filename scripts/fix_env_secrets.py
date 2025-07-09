#!/usr/bin/env python3
"""
Quick Fix Script for Environment Variables and Secret Management
===============================================================

This script automatically:
1. Scans code for hard-coded secrets and missing environment variables
2. Updates .env.example with missing keys and placeholder values
3. Replaces hard-coded secrets with os.getenv() references
4. Generates a patch report for review

Usage:
    python scripts/fix_env_secrets.py [--dry-run] [--verbose]
"""

import os
import re
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

@dataclass
class SecretMatch:
    """Represents a detected secret or environment variable usage."""
    file_path: str
    line_number: int
    line_content: str
    secret_type: str
    variable_name: str
    current_value: str
    suggested_replacement: str
    confidence: float

@dataclass
class FixReport:
    """Report of fixes applied."""
    files_modified: List[str]
    secrets_replaced: List[SecretMatch]
    env_vars_added: List[str]
    warnings: List[str]
    errors: List[str]
    timestamp: str

class SecretDetector:
    """Detects hard-coded secrets and missing environment variables."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backend_root = self.project_root / 'backend'
        self.env_example_path = self.backend_root / '.env.example'
        
        # Common secret patterns
        self.secret_patterns = {
            'openai_api_key': {
                'pattern': r'sk-[a-zA-Z0-9]{48}',
                'replacement': 'os.getenv("OPENAI_API_KEY")',
                'env_var': 'OPENAI_API_KEY',
                'placeholder': 'your_openai_api_key_here'
            },
            'supabase_anon_key': {
                'pattern': r'eyJ[a-zA-Z0-9_-]{100,}',
                'replacement': 'os.getenv("SUPABASE_ANON_KEY")',
                'env_var': 'SUPABASE_ANON_KEY',
                'placeholder': 'your_supabase_anon_key_here'
            },
            'supabase_service_key': {
                'pattern': r'eyJ[a-zA-Z0-9_-]{100,}',
                'replacement': 'os.getenv("SUPABASE_SERVICE_ROLE_KEY")',
                'env_var': 'SUPABASE_SERVICE_ROLE_KEY',
                'placeholder': 'your_supabase_service_role_key_here'
            },
            'generic_secret': {
                'pattern': r'["\'][a-zA-Z0-9_-]{32,}["\']',
                'replacement': 'os.getenv("SECRET_KEY")',
                'env_var': 'SECRET_KEY',
                'placeholder': 'your_secret_key_here'
            }
        }
        
        # Environment variable patterns to detect
        self.env_var_patterns = [
            r'os\.getenv\(["\']([A-Z_]+)["\']',
            r'os\.environ\[["\']([A-Z_]+)["\']\]',
            r'os\.environ\.get\(["\']([A-Z_]+)["\']',
            r'getenv\(["\']([A-Z_]+)["\']'
        ]
        
        # File patterns to scan
        self.file_patterns = ['*.py', '*.js', '*.ts', '*.json', '*.yaml', '*.yml']
        
        # Files/directories to skip
        self.skip_patterns = {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            '.env', '.env.local', '.env.production', 'migrations',
            'test_*', '*_test.py', 'tests'
        }

    def scan_for_secrets(self) -> List[SecretMatch]:
        """Scan codebase for hard-coded secrets."""
        matches = []
        
        for file_path in self._get_files_to_scan():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    
                    for line_no, line in enumerate(lines, 1):
                        # Skip comments and strings that are clearly not secrets
                        if self._is_comment_or_safe_string(line):
                            continue
                            
                        for secret_type, pattern_info in self.secret_patterns.items():
                            pattern = pattern_info['pattern']
                            for match in re.finditer(pattern, line):
                                # Skip if this looks like a placeholder
                                if self._is_placeholder(match.group(0)):
                                    continue
                                    
                                matches.append(SecretMatch(
                                    file_path=str(file_path),
                                    line_number=line_no,
                                    line_content=line.strip(),
                                    secret_type=secret_type,
                                    variable_name=pattern_info['env_var'],
                                    current_value=match.group(0),
                                    suggested_replacement=pattern_info['replacement'],
                                    confidence=self._calculate_confidence(line, match.group(0))
                                ))
                                
            except Exception as e:
                print(f"Error scanning {file_path}: {e}")
                
        return matches

    def scan_for_env_vars(self) -> Set[str]:
        """Scan codebase for environment variable usage."""
        env_vars = set()
        
        for file_path in self._get_files_to_scan():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for pattern in self.env_var_patterns:
                        for match in re.finditer(pattern, content):
                            env_vars.add(match.group(1))
                            
            except Exception as e:
                print(f"Error scanning {file_path}: {e}")
                
        return env_vars

    def get_current_env_vars(self) -> Dict[str, str]:
        """Get current environment variables from .env.example."""
        env_vars = {}
        
        if self.env_example_path.exists():
            try:
                with open(self.env_example_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
            except Exception as e:
                print(f"Error reading .env.example: {e}")
                
        return env_vars

    def _get_files_to_scan(self) -> List[Path]:
        """Get list of files to scan."""
        files = []
        
        for pattern in self.file_patterns:
            for file_path in self.backend_root.rglob(pattern):
                if self._should_skip_file(file_path):
                    continue
                files.append(file_path)
                
        return files

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        path_str = str(file_path)
        
        for skip_pattern in self.skip_patterns:
            if skip_pattern in path_str:
                return True
                
        return False

    def _is_comment_or_safe_string(self, line: str) -> bool:
        """Check if line is a comment or safe string."""
        stripped = line.strip()
        return (
            stripped.startswith('#') or
            stripped.startswith('//') or
            stripped.startswith('/*') or
            'placeholder' in stripped.lower() or
            'example' in stripped.lower() or
            'your_' in stripped.lower()
        )

    def _is_placeholder(self, value: str) -> bool:
        """Check if value is a placeholder."""
        placeholder_indicators = [
            'your_', 'example_', 'placeholder_', 'test_', 'demo_',
            'fake_', 'mock_', 'sample_', 'dummy_'
        ]
        
        value_lower = value.lower()
        return any(indicator in value_lower for indicator in placeholder_indicators)

    def _calculate_confidence(self, line: str, secret: str) -> float:
        """Calculate confidence that this is a real secret."""
        confidence = 0.5
        
        # Higher confidence for certain patterns
        if secret.startswith('sk-'):
            confidence += 0.3
        if secret.startswith('eyJ'):
            confidence += 0.2
        if len(secret) > 40:
            confidence += 0.1
        
        # Lower confidence for test/placeholder contexts
        if any(word in line.lower() for word in ['test', 'example', 'placeholder']):
            confidence -= 0.3
        
        return min(1.0, max(0.0, confidence))

class SecretFixer:
    """Applies fixes for secrets and environment variables."""
    
    def __init__(self, detector: SecretDetector, dry_run: bool = False):
        self.detector = detector
        self.dry_run = dry_run
        self.report = FixReport(
            files_modified=[],
            secrets_replaced=[],
            env_vars_added=[],
            warnings=[],
            errors=[],
            timestamp=datetime.now().isoformat()
        )

    def fix_secrets(self, secrets: List[SecretMatch], min_confidence: float = 0.7) -> FixReport:
        """Fix detected secrets by replacing with os.getenv calls."""
        
        # Group secrets by file
        secrets_by_file = {}
        for secret in secrets:
            if secret.confidence >= min_confidence:
                file_path = secret.file_path
                if file_path not in secrets_by_file:
                    secrets_by_file[file_path] = []
                secrets_by_file[file_path].append(secret)
        
        # Process each file
        for file_path, file_secrets in secrets_by_file.items():
            try:
                self._fix_file_secrets(file_path, file_secrets)
            except Exception as e:
                self.report.errors.append(f"Error fixing {file_path}: {str(e)}")
        
        return self.report

    def update_env_example(self, used_env_vars: Set[str]) -> None:
        """Update .env.example with missing environment variables."""
        
        current_env_vars = self.detector.get_current_env_vars()
        missing_vars = used_env_vars - set(current_env_vars.keys())
        
        if not missing_vars:
            return
        
        # Prepare new entries
        new_entries = []
        for var in sorted(missing_vars):
            placeholder = self._get_placeholder_for_var(var)
            new_entries.append(f"{var}={placeholder}")
        
        if self.dry_run:
            print(f"Would add to .env.example: {', '.join(missing_vars)}")
            return
        
        # Add to .env.example
        try:
            with open(self.detector.env_example_path, 'a') as f:
                f.write('\n# Auto-generated missing environment variables\n')
                for entry in new_entries:
                    f.write(f"{entry}\n")
                    
            self.report.env_vars_added.extend(missing_vars)
            self.report.files_modified.append(str(self.detector.env_example_path))
            
        except Exception as e:
            self.report.errors.append(f"Error updating .env.example: {str(e)}")

    def _fix_file_secrets(self, file_path: str, secrets: List[SecretMatch]) -> None:
        """Fix secrets in a specific file."""
        
        if self.dry_run:
            print(f"Would fix {len(secrets)} secrets in {file_path}")
            return
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Track if we need to add import
            needs_os_import = False
            has_os_import = 'import os' in content or 'from os import' in content
            
            # Apply replacements (in reverse order to preserve line numbers)
            for secret in reversed(sorted(secrets, key=lambda s: s.line_number)):
                line_idx = secret.line_number - 1
                old_line = lines[line_idx]
                new_line = old_line.replace(secret.current_value, secret.suggested_replacement)
                
                lines[line_idx] = new_line
                needs_os_import = True
                
                self.report.secrets_replaced.append(secret)
            
            # Add os import if needed
            if needs_os_import and not has_os_import:
                # Find the best place to insert import
                insert_idx = self._find_import_insertion_point(lines)
                lines.insert(insert_idx, 'import os')
            
            # Write back
            with open(file_path, 'w') as f:
                f.write('\n'.join(lines))
            
            self.report.files_modified.append(file_path)
            
        except Exception as e:
            self.report.errors.append(f"Error fixing {file_path}: {str(e)}")

    def _find_import_insertion_point(self, lines: List[str]) -> int:
        """Find the best place to insert os import."""
        
        # Look for existing imports
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                continue
            elif line.strip() == '' or line.strip().startswith('#'):
                continue
            else:
                return i
        
        # If no good place found, insert at the beginning
        return 0

    def _get_placeholder_for_var(self, var_name: str) -> str:
        """Get appropriate placeholder for environment variable."""
        
        placeholders = {
            'OPENAI_API_KEY': 'your_openai_api_key_here',
            'SUPABASE_URL': 'your_supabase_url_here',
            'SUPABASE_SERVICE_ROLE_KEY': 'your_supabase_service_role_key_here',
            'SUPABASE_ANON_KEY': 'your_supabase_anon_key_here',
            'REDIS_URL': 'redis://localhost:6379/0',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'REDIS_DB': '0',
            'GRAPHITI_DATABASE_URL': 'bolt://localhost:7687',
            'GRAPHITI_DATABASE_USER': 'neo4j',
            'GRAPHITI_DATABASE_PASSWORD': 'your_neo4j_password_here',
            'GRAPHITI_DATABASE_NAME': 'neo4j',
            'GRAPHITI_MAX_CONNECTIONS': '10',
            'GRAPHITI_CONNECTION_TIMEOUT': '30',
            'OPENAI_MODEL': 'gpt-4-turbo-preview',
            'OPENAI_MAX_TOKENS': '4000',
            'OPENAI_TEMPERATURE': '0.1',
            'NEO4J_URI': 'bolt://localhost:7687',
            'NEO4J_USERNAME': 'neo4j',
            'NEO4J_PASSWORD': 'your_neo4j_password_here',
            'NEO4J_DATABASE': 'neo4j'
        }
        
        return placeholders.get(var_name, f'your_{var_name.lower()}_here')

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Fix environment variables and secrets')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--min-confidence', type=float, default=0.7, help='Minimum confidence for secret replacement')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    
    args = parser.parse_args()
    
    # Initialize detector and fixer
    detector = SecretDetector(args.project_root)
    fixer = SecretFixer(detector, dry_run=args.dry_run)
    
    print("🔍 Scanning for secrets and environment variables...")
    
    # Scan for secrets
    secrets = detector.scan_for_secrets()
    if args.verbose:
        print(f"Found {len(secrets)} potential secrets")
    
    # Scan for environment variables
    env_vars = detector.scan_for_env_vars()
    if args.verbose:
        print(f"Found {len(env_vars)} environment variables in use")
    
    # Fix secrets
    if secrets:
        print(f"🔧 Fixing {len([s for s in secrets if s.confidence >= args.min_confidence])} high-confidence secrets...")
        fixer.fix_secrets(secrets, args.min_confidence)
    
    # Update .env.example
    print("📝 Updating .env.example with missing variables...")
    fixer.update_env_example(env_vars)
    
    # Generate report
    report = fixer.report
    
    print("\n📊 Fix Report:")
    print("=" * 50)
    print(f"Files modified: {len(report.files_modified)}")
    print(f"Secrets replaced: {len(report.secrets_replaced)}")
    print(f"Environment variables added: {len(report.env_vars_added)}")
    print(f"Warnings: {len(report.warnings)}")
    print(f"Errors: {len(report.errors)}")
    
    if args.verbose:
        if report.files_modified:
            print(f"\nModified files:")
            for file_path in report.files_modified:
                print(f"  - {file_path}")
        
        if report.secrets_replaced:
            print(f"\nSecrets replaced:")
            for secret in report.secrets_replaced:
                print(f"  - {secret.file_path}:{secret.line_number} ({secret.secret_type})")
        
        if report.env_vars_added:
            print(f"\nEnvironment variables added:")
            for var in report.env_vars_added:
                print(f"  - {var}")
    
    if report.warnings:
        print(f"\n⚠️  Warnings:")
        for warning in report.warnings:
            print(f"  - {warning}")
    
    if report.errors:
        print(f"\n❌ Errors:")
        for error in report.errors:
            print(f"  - {error}")
    
    # Save report
    report_path = Path(args.project_root) / 'scripts' / 'fix_report.json'
    try:
        with open(report_path, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        print(f"\n📋 Detailed report saved to: {report_path}")
    except Exception as e:
        print(f"\n❌ Error saving report: {e}")
    
    print("\n✅ Secret management fixes completed!")
    
    if args.dry_run:
        print("\nThis was a dry run. Run without --dry-run to apply changes.")

if __name__ == '__main__':
    main()
