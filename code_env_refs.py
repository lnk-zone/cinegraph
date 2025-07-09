#!/usr/bin/env python3
"""
Environment Variable Code Reference Scanner
===========================================

This script performs a recursive scan of the repository for environment variable patterns:
- os.getenv() calls
- os.environ[] calls  
- create_client(..., os.getenv) patterns
- Generic regex patterns for environment variables

Captures:
- Full variable name
- File path & line number
- Whether a default value is supplied
- Any immediate error handling (try/except, conditional checks)

Results are saved to code_env_refs.json
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict

@dataclass
class EnvironmentReference:
    """Represents a single environment variable reference in code."""
    variable_name: str
    file_path: str
    line_number: int
    line_content: str
    pattern_type: str  # 'os.getenv', 'os.environ', 'create_client', 'generic'
    has_default: bool
    default_value: Optional[str]
    error_handling: List[str]  # List of error handling patterns found
    context_lines: List[str]  # Surrounding lines for context

class EnvironmentVariableScanner:
    """Scanner for environment variable references in code."""
    
    def __init__(self, project_root: str = "/Users/shachiakyaagba/Desktop/cinegraph"):
        self.project_root = Path(project_root)
        self.references: List[EnvironmentReference] = []
        self.skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv', '.env'}
        
        # Patterns for different types of environment variable references
        self.patterns = {
            'os.getenv': [
                r'os\.getenv\(\s*["\']([^"\']+)["\']\s*(?:,\s*([^)]+))?\s*\)',
                r'getenv\(\s*["\']([^"\']+)["\']\s*(?:,\s*([^)]+))?\s*\)',
            ],
            'os.environ': [
                r'os\.environ\[\s*["\']([^"\']+)["\']\s*\]',
                r'environ\[\s*["\']([^"\']+)["\']\s*\]',
                r'os\.environ\.get\(\s*["\']([^"\']+)["\']\s*(?:,\s*([^)]+))?\s*\)',
                r'environ\.get\(\s*["\']([^"\']+)["\']\s*(?:,\s*([^)]+))?\s*\)',
            ],
            'create_client': [
                r'create_client\([^)]*os\.getenv\(\s*["\']([^"\']+)["\']\s*(?:,\s*([^)]+))?\s*\)',
                r'create_client\([^)]*os\.environ\[\s*["\']([^"\']+)["\']\s*\]',
                r'create_client\([^)]*os\.environ\.get\(\s*["\']([^"\']+)["\']\s*(?:,\s*([^)]+))?\s*\)',
            ],
            'generic': [
                r'["\']([A-Z0-9_]{3,})["\']\s*(?:,\s*([^)]+))?',  # Generic pattern for env var names
            ]
        }
        
        # Error handling patterns to look for
        self.error_patterns = [
            r'try\s*:',
            r'except\s+\w*Error',
            r'except\s+Exception',
            r'if\s+.*\s+is\s+None',
            r'if\s+not\s+',
            r'raise\s+\w*Error',
            r'\.get\(',
            r'or\s+["\']',
        ]
    
    def scan_file(self, file_path: Path) -> List[EnvironmentReference]:
        """Scan a single file for environment variable references."""
        references = []
        
        if not file_path.exists() or file_path.suffix not in ['.py', '.js', '.ts', '.jsx', '.tsx']:
            return references
            
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return references
            
        for line_num, line in enumerate(lines, 1):
            line_content = line.strip()
            
            # Skip empty lines and comments
            if not line_content or line_content.startswith('#') or line_content.startswith('//'):
                continue
                
            # Check each pattern type
            for pattern_type, patterns in self.patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, line_content, re.IGNORECASE)
                    
                    for match in matches:
                        # Extract variable name and default value
                        groups = match.groups()
                        if not groups or not groups[0]:
                            continue
                            
                        variable_name = groups[0]
                        default_value = groups[1] if len(groups) > 1 and groups[1] else None
                        has_default = default_value is not None
                        
                        # Skip if this looks like a generic pattern but doesn't seem like an env var
                        if pattern_type == 'generic':
                            # More strict filtering for generic patterns
                            if not self._is_likely_env_var(variable_name, line_content):
                                continue
                                
                        # Get context lines (3 before and after)
                        context_start = max(0, line_num - 4)
                        context_end = min(len(lines), line_num + 3)
                        context_lines = [lines[i].strip() for i in range(context_start, context_end)]
                        
                        # Check for error handling patterns in context
                        error_handling = self._find_error_handling(context_lines)
                        
                        # Create reference
                        ref = EnvironmentReference(
                            variable_name=variable_name,
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            line_content=line_content,
                            pattern_type=pattern_type,
                            has_default=has_default,
                            default_value=default_value.strip() if default_value else None,
                            error_handling=error_handling,
                            context_lines=context_lines
                        )
                        
                        references.append(ref)
        
        return references
    
    def _is_likely_env_var(self, variable_name: str, line_content: str) -> bool:
        """Check if a variable name is likely an environment variable."""
        # Must be all uppercase with underscores
        if not re.match(r'^[A-Z][A-Z0-9_]*$', variable_name):
            return False
            
        # Must be at least 3 characters
        if len(variable_name) < 3:
            return False
            
        # Must be in context that suggests environment variable usage
        env_context_keywords = [
            'getenv', 'environ', 'env', 'config', 'settings',
            'DATABASE', 'API', 'SECRET', 'KEY', 'URL', 'HOST', 'PORT',
            'REDIS', 'SUPABASE', 'OPENAI', 'NEO4J', 'GRAPHITI'
        ]
        
        line_lower = line_content.lower()
        return any(keyword.lower() in line_lower for keyword in env_context_keywords)
    
    def _find_error_handling(self, context_lines: List[str]) -> List[str]:
        """Find error handling patterns in context lines."""
        error_handling = []
        
        for line in context_lines:
            for pattern in self.error_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    error_handling.append(pattern)
                    break
        
        return list(set(error_handling))  # Remove duplicates
    
    def scan_directory(self) -> List[EnvironmentReference]:
        """Scan the entire project directory for environment variable references."""
        print(f"🔍 Scanning {self.project_root} for environment variable references...")
        
        all_references = []
        file_count = 0
        
        # Walk through all files
        for root, dirs, files in os.walk(self.project_root):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]
            
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):
                    file_path = Path(root) / file
                    file_count += 1
                    
                    file_references = self.scan_file(file_path)
                    all_references.extend(file_references)
                    
                    if file_references:
                        print(f"  📄 {file_path.relative_to(self.project_root)}: {len(file_references)} references")
        
        print(f"✅ Scanned {file_count} files, found {len(all_references)} environment variable references")
        return all_references
    
    def deduplicate_references(self, references: List[EnvironmentReference]) -> List[EnvironmentReference]:
        """Remove duplicate references (same variable, file, and line)."""
        seen = set()
        unique_refs = []
        
        for ref in references:
            key = (ref.variable_name, ref.file_path, ref.line_number)
            if key not in seen:
                seen.add(key)
                unique_refs.append(ref)
        
        return unique_refs
    
    def save_to_json(self, references: List[EnvironmentReference], output_file: str = "code_env_refs.json"):
        """Save references to JSON file."""
        output_path = self.project_root / output_file
        
        # Convert to dictionaries for JSON serialization
        data = {
            "scan_summary": {
                "total_references": len(references),
                "unique_variables": len(set(ref.variable_name for ref in references)),
                "files_with_references": len(set(ref.file_path for ref in references)),
                "pattern_types": {
                    pattern_type: len([ref for ref in references if ref.pattern_type == pattern_type])
                    for pattern_type in set(ref.pattern_type for ref in references)
                },
                "variables_with_defaults": len([ref for ref in references if ref.has_default]),
                "references_with_error_handling": len([ref for ref in references if ref.error_handling]),
            },
            "references": [asdict(ref) for ref in references],
            "variable_summary": self._create_variable_summary(references)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to {output_path}")
        return output_path
    
    def _create_variable_summary(self, references: List[EnvironmentReference]) -> Dict[str, Any]:
        """Create a summary of all unique variables found."""
        variable_summary = {}
        
        for ref in references:
            var_name = ref.variable_name
            
            if var_name not in variable_summary:
                variable_summary[var_name] = {
                    "total_references": 0,
                    "files": set(),
                    "pattern_types": set(),
                    "has_default_somewhere": False,
                    "default_values": set(),
                    "error_handling_patterns": set()
                }
            
            summary = variable_summary[var_name]
            summary["total_references"] += 1
            summary["files"].add(ref.file_path)
            summary["pattern_types"].add(ref.pattern_type)
            
            if ref.has_default:
                summary["has_default_somewhere"] = True
                if ref.default_value:
                    summary["default_values"].add(ref.default_value)
            
            summary["error_handling_patterns"].update(ref.error_handling)
        
        # Convert sets to lists for JSON serialization
        for var_name, summary in variable_summary.items():
            summary["files"] = list(summary["files"])
            summary["pattern_types"] = list(summary["pattern_types"])
            summary["default_values"] = list(summary["default_values"])
            summary["error_handling_patterns"] = list(summary["error_handling_patterns"])
        
        return variable_summary
    
    def print_summary(self, references: List[EnvironmentReference]):
        """Print a summary of the scan results."""
        print("\n" + "="*80)
        print("📊 ENVIRONMENT VARIABLE REFERENCE SCAN SUMMARY")
        print("="*80)
        
        # Basic statistics
        total_refs = len(references)
        unique_vars = len(set(ref.variable_name for ref in references))
        files_with_refs = len(set(ref.file_path for ref in references))
        
        print(f"\n📈 STATISTICS:")
        print(f"   • Total references found: {total_refs}")
        print(f"   • Unique variables: {unique_vars}")
        print(f"   • Files with references: {files_with_refs}")
        
        # Pattern type breakdown
        pattern_counts = {}
        for ref in references:
            pattern_counts[ref.pattern_type] = pattern_counts.get(ref.pattern_type, 0) + 1
        
        print(f"\n🔍 PATTERN TYPES:")
        for pattern_type, count in sorted(pattern_counts.items()):
            print(f"   • {pattern_type}: {count} references")
        
        # Default values
        with_defaults = [ref for ref in references if ref.has_default]
        print(f"\n⚙️  DEFAULT VALUES:")
        print(f"   • References with defaults: {len(with_defaults)}")
        print(f"   • References without defaults: {total_refs - len(with_defaults)}")
        
        # Error handling
        with_error_handling = [ref for ref in references if ref.error_handling]
        print(f"\n🛡️  ERROR HANDLING:")
        print(f"   • References with error handling: {len(with_error_handling)}")
        print(f"   • References without error handling: {total_refs - len(with_error_handling)}")
        
        # Top variables by usage
        var_counts = {}
        for ref in references:
            var_counts[ref.variable_name] = var_counts.get(ref.variable_name, 0) + 1
        
        print(f"\n🏆 TOP VARIABLES BY USAGE:")
        for var_name, count in sorted(var_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   • {var_name}: {count} references")
        
        print(f"\n📁 FILES WITH MOST REFERENCES:")
        file_counts = {}
        for ref in references:
            file_counts[ref.file_path] = file_counts.get(ref.file_path, 0) + 1
        
        for file_path, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   • {file_path}: {count} references")

def main():
    """Main function to run the environment variable scan."""
    print("🚀 Environment Variable Code Reference Scanner")
    print("=" * 60)
    
    # Initialize scanner
    scanner = EnvironmentVariableScanner()
    
    # Scan for references
    references = scanner.scan_directory()
    
    # Deduplicate
    references = scanner.deduplicate_references(references)
    print(f"🔄 After deduplication: {len(references)} unique references")
    
    # Save to JSON
    output_path = scanner.save_to_json(references)
    
    # Print summary
    scanner.print_summary(references)
    
    print(f"\n✅ Scan completed! Results saved to {output_path}")
    print(f"📄 You can now review the detailed results in the JSON file.")

if __name__ == "__main__":
    main()
