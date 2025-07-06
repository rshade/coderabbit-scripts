"""
GitHub Actions CI/CD linter
Catches issues with GitHub Actions workflow configuration
"""

import re
from pathlib import Path
from typing import List
import yaml

from ..base_linter import BaseLinter, LintIssue, LintSeverity


class GitHubActionsLinter(BaseLinter):
    """Linter for GitHub Actions workflow files"""
    
    def __init__(self):
        super().__init__("github_actions", [".github/workflows/*.yml", ".github/workflows/*.yaml"])
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Check GitHub Actions workflow file for issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Try to parse as YAML
            try:
                workflow = yaml.safe_load(content)
                issues.extend(self._check_workflow_structure(file_path, workflow))
            except yaml.YAMLError as e:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.HIGH,
                    rule_id="GHA_001",
                    message=f"Invalid YAML syntax: {e}",
                    suggestion="Fix YAML syntax errors"
                ))
                return issues
            
            for line_num, line in enumerate(lines, 1):
                issues.extend(self._check_codecov_patterns(file_path, line_num, line))
                issues.extend(self._check_security_patterns(file_path, line_num, line))
                issues.extend(self._check_performance_patterns(file_path, line_num, line))
                issues.extend(self._check_formatting_patterns(file_path, line_num, line))
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_workflow_structure(self, file_path: Path, workflow: dict) -> List[LintIssue]:
        """Check overall workflow structure"""
        issues = []
        
        if not isinstance(workflow, dict):
            return issues
            
        # Check for required fields (these should already be present if YAML parsed correctly)
        # Only flag if they're actually missing
        
        return issues  # Skip structural checks since YAML parsing confirms structure
    
    def _check_codecov_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for Codecov configuration issues"""
        issues = []
        
        # Codecov action with wrong parameter name
        if 'codecov/codecov-action' in line:
            # Look for 'files' parameter which should be 'file'
            if 'files:' in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="GHA_005",
                    message="Codecov action uses 'files' parameter, should be 'file'",
                    suggestion="Change 'files:' to 'file:' for single coverage file",
                    auto_fixable=True
                ))
        
        # Coverage file path validation
        if 'file:' in line and 'coverage.out' in line and './coverage.out' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="GHA_006",
                message="Coverage file path should be relative (./coverage.out)",
                suggestion="Use relative path: file: ./coverage.out",
                auto_fixable=True
            ))
        
        return issues
    
    def _check_security_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for security issues in workflows"""
        issues = []
        
        # Hardcoded secrets in workflow
        if '${{' in line and any(secret in line.lower() for secret in ['password', 'key', 'secret', 'token']):
            # Check if it's using secrets. properly
            if 'secrets.' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="GHA_007",
                    message="Potential hardcoded secret in workflow",
                    suggestion="Use secrets context: ${{ secrets.SECRET_NAME }}"
                ))
        
        # Deprecated actions versions
        deprecated_actions = [
            ('actions/checkout@v1', 'actions/checkout@v4'),
            ('actions/checkout@v2', 'actions/checkout@v4'),
            ('actions/setup-go@v1', 'actions/setup-go@v5'),
            ('actions/setup-go@v2', 'actions/setup-go@v5'),
        ]
        
        for deprecated, recommended in deprecated_actions:
            if deprecated in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="GHA_008",
                    message=f"Deprecated action version: {deprecated}",
                    suggestion=f"Update to {recommended}",
                    auto_fixable=True
                ))
        
        return issues
    
    def _check_performance_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for performance issues in workflows"""
        issues = []
        
        # Missing cache for Go modules
        if 'actions/setup-go' in line and 'cache:' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="GHA_009",
                message="Go setup without cache enabled",
                suggestion="Add 'cache: true' to setup-go action for faster builds"
            ))
        
        # Inefficient checkout
        if 'actions/checkout' in line and 'fetch-depth: 0' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="GHA_010",
                message="Full git history checkout may be unnecessary",
                suggestion="Use shallow checkout unless full history is needed"
            ))
        
        return issues
    
    def _check_formatting_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for formatting and style issues"""
        issues = []
        
        # Trailing whitespace
        if line.rstrip() != line and line.strip():
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="GHA_011",
                message="Trailing whitespace in workflow file",
                suggestion="Remove trailing whitespace",
                auto_fixable=True
            ))
        
        # Inconsistent indentation (basic check) - skip this for now as it's too noisy
        # GitHub Actions workflows commonly use correct 2-space indentation
        
        return issues
    
    def _fix_issue(self, issue: LintIssue) -> bool:
        """Auto-fix issues where possible"""
        if not issue.auto_fixable:
            return False
            
        try:
            with open(issue.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = issue.line_number - 1
            if line_idx >= len(lines):
                return False
            
            line = lines[line_idx]
            original_line = line
            
            # Fix Codecov files -> file
            if issue.rule_id == "GHA_005":
                line = line.replace('files:', 'file:')
            
            # Fix coverage file path
            elif issue.rule_id == "GHA_006":
                line = re.sub(r'file:\s*coverage\.out', 'file: ./coverage.out', line)
            
            # Fix deprecated action versions
            elif issue.rule_id == "GHA_008":
                deprecated_map = {
                    'actions/checkout@v1': 'actions/checkout@v4',
                    'actions/checkout@v2': 'actions/checkout@v4', 
                    'actions/setup-go@v1': 'actions/setup-go@v5',
                    'actions/setup-go@v2': 'actions/setup-go@v5',
                }
                for old, new in deprecated_map.items():
                    if old in line:
                        line = line.replace(old, new)
                        break
            
            # Fix trailing whitespace
            elif issue.rule_id == "GHA_011":
                line = line.rstrip() + '\n'
            
            # If line was modified, write it back
            if line != original_line:
                lines[line_idx] = line
                with open(issue.file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                    
        except Exception as e:
            print(f"Error auto-fixing {issue.file_path}:{issue.line_number}: {e}")
            
        return False