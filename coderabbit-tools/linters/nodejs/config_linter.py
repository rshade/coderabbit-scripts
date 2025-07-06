"""
Node.js Configuration Linter
Catches issues in package.json, commitlint.config.js, and other Node.js configuration files
Based on CodeRabbit issues: Fix #4 (commitlint redundant values), Fix #22 (package version updates)
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any

from ..base_linter import NodeJSLinter, LintIssue, LintSeverity


class NodeConfigLinter(NodeJSLinter):
    """Linter for Node.js configuration files"""
    
    def __init__(self):
        super().__init__("node_config", ["package.json", "*.config.js", "*.config.ts"])
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Check Node.js configuration file for issues"""
        issues = []
        
        if file_path.name == "package.json":
            issues.extend(self._check_package_json(file_path))
        elif file_path.name == "commitlint.config.js":
            issues.extend(self._check_commitlint_config(file_path))
        elif file_path.name.endswith('.config.js') or file_path.name.endswith('.config.ts'):
            issues.extend(self._check_general_config(file_path))
        
        return issues
    
    def _check_package_json(self, file_path: Path) -> List[LintIssue]:
        """Check package.json for issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                package_data = json.loads(content)
            
            # Check for outdated dependencies
            issues.extend(self._check_outdated_dependencies(file_path, package_data))
            
            # Check for missing required fields
            issues.extend(self._check_required_fields(file_path, package_data))
            
            # Check for security vulnerabilities
            issues.extend(self._check_security_issues(file_path, package_data))
            
            # Check for formatting issues
            issues.extend(self._check_json_formatting(file_path, content))
            
        except json.JSONDecodeError as e:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=getattr(e, 'lineno', 1),
                severity=LintSeverity.HIGH,
                rule_id="CONFIG_001",
                message=f"Invalid JSON syntax: {e.msg}",
                suggestion="Fix JSON syntax error"
            ))
        except Exception as e:
            print(f"Error reading package.json {file_path}: {e}")
        
        return issues
    
    def _check_commitlint_config(self, file_path: Path) -> List[LintIssue]:
        """Check commitlint.config.js for issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                # Check for redundant default values
                if re.search(r'100', line) and ('max-line-length' in line or 'line-length' in line):
                    # Check if it's setting the default value of 100
                    if 'always' in line and '100' in line:
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.MEDIUM,
                            rule_id="CONFIG_002",
                            message="Redundant default value of 100 in commitlint config",
                            suggestion="Remove redundant default values or use explicit non-default values",
                            auto_fixable=True
                        ))
                
                # Check for trailing commas in wrong places
                if line.strip().endswith(',') and line_num == len(lines):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="CONFIG_003",
                        message="Trailing comma in final object property",
                        suggestion="Remove trailing comma from final property",
                        auto_fixable=True
                    ))
                
                # Check for missing extends configuration
                if 'module.exports' in line and 'extends' not in content:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="CONFIG_004",
                        message="Commitlint config without extends base configuration",
                        suggestion="Add extends: ['@commitlint/config-conventional'] for standard rules"
                    ))
        
        except Exception as e:
            print(f"Error reading commitlint config {file_path}: {e}")
        
        return issues
    
    def _check_general_config(self, file_path: Path) -> List[LintIssue]:
        """Check general config files for common issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                # Check for hardcoded sensitive values
                if re.search(r'(password|secret|key|token)\s*[:=]\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                    if 'process.env' not in line and 'example' not in line.lower():
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.HIGH,
                            rule_id="CONFIG_005",
                            message="Hardcoded sensitive value in config",
                            suggestion="Use environment variables for sensitive configuration values"
                        ))
                
                # Check for missing error handling in async config
                if 'async' in line and 'catch' not in content:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="CONFIG_006",
                        message="Async configuration without error handling",
                        suggestion="Add try-catch or .catch() for async configuration operations"
                    ))
        
        except Exception as e:
            print(f"Error reading config file {file_path}: {e}")
        
        return issues
    
    def _check_outdated_dependencies(self, file_path: Path, package_data: Dict[str, Any]) -> List[LintIssue]:
        """Check for outdated dependencies"""
        issues = []
        
        # Common dependencies that should be updated
        outdated_patterns = {
            'testify': {
                'current_pattern': r'^1\.1[01]\.0$',
                'recommendation': 'v1.10.0 (latest stable)',
                'severity': LintSeverity.MEDIUM
            },
            'react': {
                'current_pattern': r'^1[67]\..*',
                'recommendation': 'v18.x for latest features',
                'severity': LintSeverity.MEDIUM
            },
            'node': {
                'current_pattern': r'^1[24]\..*',
                'recommendation': 'v18 or v20 LTS',
                'severity': LintSeverity.MEDIUM
            }
        }
        
        for section in ['dependencies', 'devDependencies', 'peerDependencies']:
            if section in package_data:
                for dep_name, version in package_data[section].items():
                    if dep_name in outdated_patterns:
                        pattern_info = outdated_patterns[dep_name]
                        if re.match(pattern_info['current_pattern'], version.lstrip('^~')):
                            issues.append(self._create_issue(
                                file_path=file_path,
                                line_number=1,  # JSON line numbers are complex
                                severity=pattern_info['severity'],
                                rule_id="CONFIG_007",
                                message=f"Potentially outdated dependency: {dep_name}@{version}",
                                suggestion=f"Consider updating to {pattern_info['recommendation']}"
                            ))
        
        return issues
    
    def _check_required_fields(self, file_path: Path, package_data: Dict[str, Any]) -> List[LintIssue]:
        """Check for missing required fields in package.json"""
        issues = []
        
        required_fields = ['name', 'version']
        recommended_fields = ['description', 'author', 'license']
        
        for field in required_fields:
            if field not in package_data:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.HIGH,
                    rule_id="CONFIG_008",
                    message=f"Missing required field: {field}",
                    suggestion=f"Add {field} field to package.json"
                ))
        
        for field in recommended_fields:
            if field not in package_data:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.LOW,
                    rule_id="CONFIG_009",
                    message=f"Missing recommended field: {field}",
                    suggestion=f"Consider adding {field} field to package.json"
                ))
        
        return issues
    
    def _check_security_issues(self, file_path: Path, package_data: Dict[str, Any]) -> List[LintIssue]:
        """Check for security issues in package.json"""
        issues = []
        
        # Check for overly permissive version ranges
        for section in ['dependencies', 'devDependencies']:
            if section in package_data:
                for dep_name, version in package_data[section].items():
                    if version.startswith('*') or version.startswith('>='):
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=1,
                            severity=LintSeverity.MEDIUM,
                            rule_id="CONFIG_010",
                            message=f"Overly permissive version range for {dep_name}: {version}",
                            suggestion="Use more specific version ranges for security"
                        ))
        
        # Check for missing security scripts
        if 'scripts' in package_data:
            has_security_audit = any('audit' in script for script in package_data['scripts'].values())
            if not has_security_audit:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.LOW,
                    rule_id="CONFIG_011",
                    message="No security audit script found",
                    suggestion="Add 'audit': 'npm audit' to scripts for security checking"
                ))
        
        return issues
    
    def _check_json_formatting(self, file_path: Path, content: str) -> List[LintIssue]:
        """Check JSON formatting issues"""
        issues = []
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines, 1):
            # Check for trailing commas (not allowed in JSON)
            if line.strip().endswith(',') and line_num < len(lines):
                next_line = lines[line_num].strip() if line_num < len(lines) else ""
                if next_line in ['}', ']']:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.HIGH,
                        rule_id="CONFIG_012",
                        message="Trailing comma before closing bracket/brace",
                        suggestion="Remove trailing comma (not valid in JSON)",
                        auto_fixable=True
                    ))
        
        return issues
    
    def _fix_issue(self, issue: LintIssue) -> bool:
        """Auto-fix specific configuration issues"""
        try:
            with open(issue.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = issue.line_number - 1
            if line_idx >= len(lines):
                return False
            
            if issue.rule_id == "CONFIG_002":  # Remove redundant commitlint values
                line = lines[line_idx]
                if "'body-max-line-length': [0, 'always']" in line:
                    # Remove the entire line
                    lines.pop(line_idx)
                elif "'footer-max-line-length': [0, 'always']" in line:
                    # Remove the entire line
                    lines.pop(line_idx)
                
            elif issue.rule_id == "CONFIG_003":  # Remove trailing comma
                lines[line_idx] = lines[line_idx].rstrip(',\n') + '\n'
                
            elif issue.rule_id == "CONFIG_012":  # Remove trailing comma in JSON
                lines[line_idx] = lines[line_idx].rstrip(',\n') + '\n'
            
            else:
                return False
            
            with open(issue.file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
            
        except Exception as e:
            print(f"Error fixing {issue.file_path}: {e}")
            return False