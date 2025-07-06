#!/usr/bin/env python3
"""
CodeRabbit Linter - Pre-commit linting to catch common CodeRabbit issues
Designed to prevent the develop -> commit -> CodeRabbit -> fix cycle

Usage:
    python coderabbit_linter.py [--path PATH] [--linters LINTERS] [--fix]
    
Examples:
    python coderabbit_linter.py                                    # Lint current directory
    python coderabbit_linter.py --path /path/to/project            # Lint specific path
    python coderabbit_linter.py --linters go_module,security       # Run specific linters
    python coderabbit_linter.py --fix                              # Auto-fix issues where possible
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Import all linters
from linters.golang.go_module_linter import GoModuleLinter
from linters.golang.security_linter import SecurityLinter
from linters.golang.context_linter import ContextLinter
from linters.golang.format_linter import FormatLinter
from linters.golang.test_linter import TestLinter
from linters.golang.http_client_linter import HttpClientLinter
from linters.golang.test_performance_linter import TestPerformanceLinter
from linters.golang.error_handling_linter import ErrorHandlingLinter
from linters.golang.unicode_linter import UnicodeStringLinter
from linters.golang.database_linter import DatabasePerformanceLinter
from linters.golang.duplication_linter import DuplicationLinter
from linters.cicd.github_actions_linter import GitHubActionsLinter
from linters.cicd.yaml_linter import YAMLLinter
from linters.markdown.markdownlint_linter import MarkdownLintLinter
from linters.nodejs.package_linter import PackageLinter
from linters.nodejs.yaml_linter import YamlLinter
from linters.nodejs.config_linter import NodeConfigLinter
from linters.nodejs.typescript_linter import TypeScriptLinter
from linters.nodejs.react_linter import ReactLinter
from linters.nodejs.security_linter import NodeJSSecurityLinter
from linters.nodejs.performance_linter import NodeJSPerformanceLinter
from linters.nodejs.accessibility_linter import AccessibilityLinter
from linters.base_linter import LintIssue, LintSeverity

class CodeRabbitLinter:
    """Main linter orchestrator that runs all configured linters"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.linters = {
            # Go linters
            'go_module': GoModuleLinter(),
            'go_security': SecurityLinter(),
            'go_context': ContextLinter(),
            'go_format': FormatLinter(),
            'go_test': TestLinter(),
            'go_http_client': HttpClientLinter(),
            'go_test_performance': TestPerformanceLinter(),
            'go_error_handling': ErrorHandlingLinter(),
            'go_unicode': UnicodeStringLinter(),
            'go_database': DatabasePerformanceLinter(),
            'go_duplication': DuplicationLinter(),
            
            # CI/CD linters  
            'github_actions': GitHubActionsLinter(),
            'yaml': YAMLLinter(),
            
            # Markdown linters
            'markdownlint': MarkdownLintLinter(),
            
            # Node.js linters
            'node_package': PackageLinter(),
            'node_yaml': YamlLinter(),
            'node_config': NodeConfigLinter(),
            'typescript': TypeScriptLinter(),
            'react': ReactLinter(),
            'node_security': NodeJSSecurityLinter(),
            'node_performance': NodeJSPerformanceLinter(),
            'accessibility': AccessibilityLinter(),
        }
        
    def run_linters(self, linter_names: List[str] = None, auto_fix: bool = False) -> List[LintIssue]:
        """Run specified linters or all linters if none specified"""
        if linter_names is None:
            linter_names = list(self.linters.keys())
            
        all_issues = []
        
        for linter_name in linter_names:
            if linter_name not in self.linters:
                print(f"Warning: Unknown linter '{linter_name}', skipping")
                continue
                
            print(f"Running {linter_name} linter...")
            linter = self.linters[linter_name]
            issues = linter.lint(self.project_path)
            
            if auto_fix:
                fixed_count = linter.fix_issues(issues, self.project_path)
                if fixed_count > 0:
                    print(f"  Fixed {fixed_count} issues automatically")
                    # Re-run linter to get remaining issues
                    issues = linter.lint(self.project_path)
            
            all_issues.extend(issues)
            print(f"  Found {len(issues)} issues")
        
        return all_issues
    
    def fix_issues(self, issues: List[LintIssue], project_path: Path) -> int:
        """Auto-fix issues where possible. Returns count of fixed issues."""
        fixed_count = 0
        
        # Group issues by linter
        issues_by_linter = {}
        for issue in issues:
            linter_name = None
            # Find the linter that created this issue
            for name, linter in self.linters.items():
                if linter.name == issue.linter_name:
                    linter_name = name
                    break
            
            if linter_name:
                if linter_name not in issues_by_linter:
                    issues_by_linter[linter_name] = []
                issues_by_linter[linter_name].append(issue)
        
        # Fix issues using their respective linters
        for linter_name, linter_issues in issues_by_linter.items():
            if linter_name in self.linters:
                linter = self.linters[linter_name]
                fixed_count += linter.fix_issues(linter_issues, project_path)
        
        return fixed_count
    
    def print_results(self, issues: List[LintIssue]) -> None:
        """Print formatted linting results"""
        if not issues:
            print("\n✅ No issues found! CodeRabbit should be happy.")
            return
            
        # Group issues by severity
        by_severity = {
            LintSeverity.HIGH: [],
            LintSeverity.MEDIUM: [],
            LintSeverity.LOW: []
        }
        
        for issue in issues:
            by_severity[issue.severity].append(issue)
        
        total = len(issues)
        high_count = len(by_severity[LintSeverity.HIGH])
        medium_count = len(by_severity[LintSeverity.MEDIUM])
        low_count = len(by_severity[LintSeverity.LOW])
        
        print(f"\n🔍 Found {total} issues:")
        print(f"  🔴 {high_count} high priority")
        print(f"  🟡 {medium_count} medium priority") 
        print(f"  🟢 {low_count} low priority")
        print()
        
        # Print issues by severity
        for severity in [LintSeverity.HIGH, LintSeverity.MEDIUM, LintSeverity.LOW]:
            severity_issues = by_severity[severity]
            if not severity_issues:
                continue
                
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[severity.value]
            print(f"{emoji} {severity.value.upper()} PRIORITY ISSUES:")
            
            for issue in severity_issues:
                try:
                    file_path = issue.file_path.relative_to(self.project_path)
                except (ValueError, AttributeError):
                    # Handle cases where file_path is not a valid Path or not relative to project_path
                    file_path = str(issue.file_path)
                print(f"  {file_path}:{issue.line_number}")
                print(f"    {issue.message}")
                if issue.suggestion:
                    print(f"    💡 {issue.suggestion}")
                print()

def main():
    parser = argparse.ArgumentParser(description="CodeRabbit Linter - Catch issues before commit")
    parser.add_argument('--path', default='.', help='Path to project directory (default: current directory)')
    parser.add_argument('--linters', help='Comma-separated list of linters to run (default: all)')
    parser.add_argument('--fix', action='store_true', help='Auto-fix issues where possible')
    parser.add_argument('--list-linters', action='store_true', help='List available linters')
    
    args = parser.parse_args()
    
    if args.list_linters:
        print("Available linters:")
        print("\n  Go linters:")
        print("    go_module         - Go module and dependency issues")
        print("    go_security       - Security vulnerabilities (JWT, secrets, etc.)")
        print("    go_context        - Go context handling patterns")
        print("    go_format         - Go code formatting and style issues")
        print("    go_test           - Go testing best practices and patterns")
        print("    go_http_client    - HTTP client configuration and patterns")
        print("    go_test_performance - Test performance (t.Parallel, cleanup, etc.)")
        print("    go_error_handling - Error wrapping and sentinel error patterns")
        print("    go_unicode        - Unicode/string handling and validation")
        print("    go_database       - Database performance and N+1 query detection")
        print("    go_duplication    - Code duplication and missing helper functions")
        print("\n  CI/CD linters:")
        print("    github_actions    - GitHub Actions workflow configuration")
        print("    yaml              - YAML formatting and CI/CD configuration")
        print("\n  Markdown linters:")
        print("    markdownlint      - Markdown formatting (uses markdownlint-cli)")
        print("\n  Node.js/TypeScript/React linters:")
        print("    node_package      - package.json and dependency issues")
        print("    node_yaml         - Node.js specific YAML configurations")
        print("    node_config       - Configuration files (commitlint, etc.)")
        print("    typescript        - TypeScript type safety and best practices")
        print("    react             - React performance, hooks rules, and patterns")
        print("    node_security     - JavaScript/TypeScript security vulnerabilities")
        print("    node_performance  - Bundle size, memory leaks, and performance")
        print("    accessibility     - Web accessibility (a11y) compliance")
        return
    
    # Determine which linters to run
    linter_names = None
    if args.linters:
        linter_names = [name.strip() for name in args.linters.split(',')]
    
    # Initialize and run linter
    linter = CodeRabbitLinter(args.path)
    issues = linter.run_linters(linter_names, args.fix)
    linter.print_results(issues)
    
    # Exit with error code if critical issues found
    critical_issues = [i for i in issues if i.severity == LintSeverity.HIGH]
    if critical_issues:
        print(f"❌ {len(critical_issues)} critical issues must be fixed before commit")
        sys.exit(1)
    elif issues:
        print(f"⚠️  {len(issues)} issues found - review before commit")
        sys.exit(0)
    else:
        print("✅ All checks passed - ready to commit!")
        sys.exit(0)

if __name__ == '__main__':
    main()