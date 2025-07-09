#!/usr/bin/env python3
"""
Environment Variables Analysis for CineGraph Project
====================================================

This script collects and parses environment variables from:
1. .env files (actual values)
2. .env.example files (placeholder values)
3. Project source code (os.getenv() calls)

The results are stored in structured Python sets for cross-comparison.
"""

import os
import re
from typing import Dict, Set, List, Any
from pathlib import Path

class EnvironmentVariableCollector:
    """Collector for environment variables from various sources."""
    
    def __init__(self, project_root: str = "/Users/shachiakyaagba/Desktop/cinegraph"):
        self.project_root = Path(project_root)
        self.env_vars: Dict[str, str] = {}
        self.env_example_vars: Dict[str, str] = {}
        self.code_referenced_vars: Set[str] = set()
        self.infrastructure_vars: Set[str] = set()
        
    def parse_env_file(self, file_path: Path) -> Dict[str, str]:
        """Parse a .env file and return variable name-value pairs."""
        variables = {}
        
        if not file_path.exists():
            return variables
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Handle variable assignments
                    if '=' in line:
                        # Split on first = only
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        variables[key] = value
                        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
        return variables
    
    def extract_getenv_calls(self, file_path: Path) -> Set[str]:
        """Extract os.getenv() calls from Python source files."""
        variables = set()
        
        if not file_path.exists() or file_path.suffix != '.py':
            return variables
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Patterns to match os.getenv() calls
            patterns = [
                r'os\.getenv\(["\']([^"\']+)["\']',  # os.getenv("VAR")
                r'os\.environ\[["\'](.*?)["\']\]',    # os.environ["VAR"]
                r'os\.environ\.get\(["\']([^"\']+)["\']',  # os.environ.get("VAR")
                r'getenv\(["\']([^"\']+)["\']',       # getenv("VAR") (direct import)
                r'environ\[["\'](.*?)["\']\]',        # environ["VAR"] (direct import)
                r'environ\.get\(["\']([^"\']+)["\']', # environ.get("VAR") (direct import)
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                variables.update(matches)
                
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
        return variables
    
    def scan_project_files(self):
        """Scan all Python files in the project for environment variable references."""
        print("🔍 Scanning project files for environment variable references...")
        
        # Skip these directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
        
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Remove skip directories from dirs list
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        print(f"Found {len(python_files)} Python files to analyze")
        
        for py_file in python_files:
            vars_in_file = self.extract_getenv_calls(py_file)
            self.code_referenced_vars.update(vars_in_file)
            
            if vars_in_file:
                print(f"  📄 {py_file.relative_to(self.project_root)}: {len(vars_in_file)} variables")
    
    def collect_all_sources(self):
        """Collect environment variables from all sources."""
        print("🚀 Collecting environment variables from all sources...")
        
        # 1. Parse .env files
        print("\n1. Parsing .env files...")
        env_file = self.project_root / "backend" / ".env"
        if env_file.exists():
            self.env_vars = self.parse_env_file(env_file)
            print(f"   ✅ .env: {len(self.env_vars)} variables")
        else:
            print("   ❌ .env file not found")
        
        env_example_file = self.project_root / "backend" / ".env.example"
        if env_example_file.exists():
            self.env_example_vars = self.parse_env_file(env_example_file)
            print(f"   ✅ .env.example: {len(self.env_example_vars)} variables")
        else:
            print("   ❌ .env.example file not found")
        
        # 2. Scan project source code
        print("\n2. Scanning project source code...")
        self.scan_project_files()
        print(f"   ✅ Code references: {len(self.code_referenced_vars)} unique variables")
        
        # 3. Look for infrastructure files (Docker, CI/CD, etc.)
        print("\n3. Scanning for infrastructure files...")
        self.scan_infrastructure_files()
        print(f"   ✅ Infrastructure references: {len(self.infrastructure_vars)} variables")
    
    def scan_infrastructure_files(self):
        """Scan for environment variables in infrastructure files."""
        # Docker files
        docker_patterns = [
            r'ENV\s+([A-Z_][A-Z0-9_]*)',  # ENV VAR_NAME
            r'--env\s+([A-Z_][A-Z0-9_]*)',  # --env VAR_NAME
            r'\$\{([A-Z_][A-Z0-9_]*)\}',   # ${VAR_NAME}
        ]
        
        # GitHub Actions files
        github_patterns = [
            r'env:\s*\n\s*([A-Z_][A-Z0-9_]*):',  # env: VAR_NAME:
            r'\$\{\{\s*env\.([A-Z_][A-Z0-9_]*)\s*\}\}',  # ${{ env.VAR_NAME }}
        ]
        
        # Look for these file patterns
        file_patterns = [
            "**/Dockerfile*",
            "**/docker-compose*.yml",
            "**/docker-compose*.yaml",
            "**/.github/workflows/*.yml",
            "**/.github/workflows/*.yaml",
            "**/docker-compose.override.yml",
        ]
        
        for pattern in file_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    self.extract_infrastructure_vars(file_path, docker_patterns + github_patterns)
    
    def extract_infrastructure_vars(self, file_path: Path, patterns: List[str]):
        """Extract environment variables from infrastructure files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                self.infrastructure_vars.update(matches)
                
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
    
    def generate_structured_lists(self) -> Dict[str, Any]:
        """Generate structured lists for cross-comparison."""
        
        # Convert to sets for easier comparison
        env_vars_set = set(self.env_vars.keys())
        env_example_vars_set = set(self.env_example_vars.keys())
        
        # Find variables that are:
        # 1. In .env but not in .env.example
        # 2. In .env.example but not in .env
        # 3. Referenced in code but not in either .env file
        # 4. In .env files but not referenced in code
        
        only_in_env = env_vars_set - env_example_vars_set
        only_in_example = env_example_vars_set - env_vars_set
        in_both_env_files = env_vars_set & env_example_vars_set
        
        referenced_not_in_env = self.code_referenced_vars - env_vars_set - env_example_vars_set
        in_env_not_referenced = env_vars_set - self.code_referenced_vars
        in_example_not_referenced = env_example_vars_set - self.code_referenced_vars
        
        return {
            'env_vars': self.env_vars,
            'env_example_vars': self.env_example_vars,
            'code_referenced_vars': self.code_referenced_vars,
            'infrastructure_vars': self.infrastructure_vars,
            'analysis': {
                'only_in_env': only_in_env,
                'only_in_example': only_in_example,
                'in_both_env_files': in_both_env_files,
                'referenced_not_in_env': referenced_not_in_env,
                'in_env_not_referenced': in_env_not_referenced,
                'in_example_not_referenced': in_example_not_referenced,
            }
        }
    
    def print_analysis_report(self, structured_data: Dict[str, Any]):
        """Print a comprehensive analysis report."""
        print("\n" + "="*80)
        print("🔍 ENVIRONMENT VARIABLES ANALYSIS REPORT")
        print("="*80)
        
        env_vars = structured_data['env_vars']
        env_example_vars = structured_data['env_example_vars']
        code_referenced_vars = structured_data['code_referenced_vars']
        infrastructure_vars = structured_data['infrastructure_vars']
        analysis = structured_data['analysis']
        
        print(f"\n📊 SUMMARY:")
        print(f"   • Variables in .env: {len(env_vars)}")
        print(f"   • Variables in .env.example: {len(env_example_vars)}")
        print(f"   • Variables referenced in code: {len(code_referenced_vars)}")
        print(f"   • Variables in infrastructure files: {len(infrastructure_vars)}")
        
        print(f"\n📋 VARIABLES IN .ENV:")
        for var, value in sorted(env_vars.items()):
            # Mask sensitive values
            if any(sensitive in var.lower() for sensitive in ['password', 'key', 'secret', 'token']):
                masked_value = f"{'*' * 8}{value[-4:] if len(value) > 4 else '***'}"
                print(f"   • {var} = {masked_value}")
            else:
                print(f"   • {var} = {value}")
        
        print(f"\n📋 VARIABLES IN .ENV.EXAMPLE:")
        for var, value in sorted(env_example_vars.items()):
            print(f"   • {var} = {value}")
        
        print(f"\n📋 VARIABLES REFERENCED IN CODE:")
        for var in sorted(code_referenced_vars):
            print(f"   • {var}")
        
        if infrastructure_vars:
            print(f"\n📋 VARIABLES IN INFRASTRUCTURE FILES:")
            for var in sorted(infrastructure_vars):
                print(f"   • {var}")
        
        print(f"\n🔍 CROSS-COMPARISON ANALYSIS:")
        
        if analysis['only_in_env']:
            print(f"\n⚠️  Variables in .env but NOT in .env.example ({len(analysis['only_in_env'])}):")
            for var in sorted(analysis['only_in_env']):
                print(f"   • {var}")
        
        if analysis['only_in_example']:
            print(f"\n⚠️  Variables in .env.example but NOT in .env ({len(analysis['only_in_example'])}):")
            for var in sorted(analysis['only_in_example']):
                print(f"   • {var}")
        
        if analysis['referenced_not_in_env']:
            print(f"\n❌ Variables referenced in code but NOT in any .env file ({len(analysis['referenced_not_in_env'])}):")
            for var in sorted(analysis['referenced_not_in_env']):
                print(f"   • {var}")
        
        if analysis['in_env_not_referenced']:
            print(f"\n❓ Variables in .env but NOT referenced in code ({len(analysis['in_env_not_referenced'])}):")
            for var in sorted(analysis['in_env_not_referenced']):
                print(f"   • {var}")
        
        if analysis['in_example_not_referenced']:
            print(f"\n❓ Variables in .env.example but NOT referenced in code ({len(analysis['in_example_not_referenced'])}):")
            for var in sorted(analysis['in_example_not_referenced']):
                print(f"   • {var}")
        
        print(f"\n✅ Variables present in both .env and .env.example ({len(analysis['in_both_env_files'])}):")
        for var in sorted(analysis['in_both_env_files']):
            print(f"   • {var}")
        
        print(f"\n📊 RECOMMENDATIONS:")
        if analysis['referenced_not_in_env']:
            print("   🔧 Add missing variables to .env.example with placeholder values")
        if analysis['only_in_env']:
            print("   📝 Consider adding variables to .env.example for documentation")
        if analysis['in_env_not_referenced']:
            print("   🧹 Consider removing unused variables from .env")
        if not (analysis['referenced_not_in_env'] or analysis['only_in_env'] or analysis['in_env_not_referenced']):
            print("   ✅ Environment variable configuration looks well-maintained!")

def main():
    """Main function to run the analysis."""
    collector = EnvironmentVariableCollector()
    collector.collect_all_sources()
    structured_data = collector.generate_structured_lists()
    collector.print_analysis_report(structured_data)
    
    print(f"\n🎯 STRUCTURED DATA FOR CROSS-COMPARISON:")
    print("="*80)
    print("# The following Python sets can be used for programmatic comparison:")
    print()
    print("# Variables from .env file:")
    print(f"env_vars = {set(structured_data['env_vars'].keys())}")
    print()
    print("# Variables from .env.example file:")
    print(f"env_example_vars = {structured_data['env_example_vars'].keys()}")
    print()
    print("# Variables referenced in source code:")
    print(f"code_referenced_vars = {structured_data['code_referenced_vars']}")
    print()
    print("# Variables in infrastructure files:")
    print(f"infrastructure_vars = {structured_data['infrastructure_vars']}")
    print()
    print("# Analysis results:")
    print(f"analysis = {structured_data['analysis']}")

if __name__ == "__main__":
    main()
