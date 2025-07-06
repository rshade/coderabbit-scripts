"""
YAML Linter for CI/CD and Configuration Files
Catches YAML formatting, GitHub Actions, and configuration issues
Based on CodeRabbit issues: Fix #3 (YAML indentation), Fix #32 (YAML formatting)
"""

import re
import yaml
from pathlib import Path
from typing import List, Dict, Any

from ..base_linter import BaseLinter, LintIssue, LintSeverity


class YAMLLinter(BaseLinter):
    """Linter for YAML formatting and CI/CD configuration issues"""
    
    def __init__(self):
        super().__init__("yaml", ["*.yml", "*.yaml"])
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Check YAML file for formatting and configuration issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Check YAML syntax first
            issues.extend(self._check_yaml_syntax(file_path, content))
            
            # Check indentation issues
            issues.extend(self._check_indentation(file_path, lines))
            
            # Check GitHub Actions specific issues
            if '.github/workflows' in str(file_path):
                issues.extend(self._check_github_actions(file_path, lines, content))
            
            # Check general YAML best practices
            issues.extend(self._check_yaml_best_practices(file_path, lines))
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_yaml_syntax(self, file_path: Path, content: str) -> List[LintIssue]:
        """Check for YAML syntax errors"""
        issues = []
        
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            line_num = getattr(e, 'problem_mark', None)
            if line_num:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num.line + 1,
                    severity=LintSeverity.HIGH,
                    rule_id="YAML_001",
                    message=f"YAML syntax error: {e.problem}",
                    suggestion="Fix YAML syntax error"
                ))
            else:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.HIGH,
                    rule_id="YAML_001",
                    message=f"YAML syntax error: {str(e)}",
                    suggestion="Fix YAML syntax error"
                ))
        
        return issues
    
    def _check_indentation(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for proper YAML indentation"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue
                
            # Check for tabs
            if '\t' in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="YAML_002",
                    message="YAML uses tabs instead of spaces",
                    suggestion="Replace tabs with spaces for YAML indentation",
                    auto_fixable=True
                ))
            
            # Check for inconsistent indentation
            leading_spaces = len(line) - len(line.lstrip())
            if leading_spaces > 0 and leading_spaces % 2 != 0:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="YAML_003",
                    message="YAML indentation should be multiples of 2 spaces",
                    suggestion="Use 2-space indentation consistently",
                    auto_fixable=True
                ))
        
        return issues
    
    def _check_github_actions(self, file_path: Path, lines: List[str], content: str) -> List[LintIssue]:
        """Check GitHub Actions specific issues"""
        issues = []
        
        try:
            yaml_data = yaml.safe_load(content)
        except:
            return issues  # Skip if YAML is invalid
        
        for line_num, line in enumerate(lines, 1):
            # Check for proper steps indentation (6 spaces)
            if re.match(r'\s*-\s*(name|uses|run|with):', line):
                leading_spaces = len(line) - len(line.lstrip())
                expected_spaces = 6  # GitHub Actions steps should be indented 6 spaces
                
                if leading_spaces != expected_spaces and 'steps:' not in lines[max(0, line_num-10):line_num]:
                    # Only check if we're actually in a steps section
                    for i in range(max(0, line_num-10), line_num):
                        if i < len(lines) and 'steps:' in lines[i]:
                            issues.append(self._create_issue(
                                file_path=file_path,
                                line_number=line_num,
                                severity=LintSeverity.HIGH,
                                rule_id="YAML_004",
                                message=f"GitHub Actions steps should be indented 6 spaces, found {leading_spaces}",
                                suggestion="Use 6-space indentation for GitHub Actions steps",
                                auto_fixable=True
                            ))
                            break
            
            # Check for trailing spaces
            if line.endswith(' ') or line.endswith('\t'):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="YAML_005",
                    message="Line has trailing whitespace",
                    suggestion="Remove trailing whitespace",
                    auto_fixable=True
                ))
            
            # Check for deprecated GitHub Actions patterns
            if 'actions/checkout@v' in line:
                version_match = re.search(r'actions/checkout@v(\d+)', line)
                if version_match and int(version_match.group(1)) < 4:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="YAML_006",
                        message="Using outdated actions/checkout version",
                        suggestion="Update to actions/checkout@v4 or later"
                    ))
            
            # Check for missing permissions
            if yaml_data and 'jobs' in yaml_data:
                if 'permissions' not in yaml_data:
                    for job_name, job_config in yaml_data['jobs'].items():
                        if isinstance(job_config, dict) and 'permissions' not in job_config:
                            issues.append(self._create_issue(
                                file_path=file_path,
                                line_number=line_num,
                                severity=LintSeverity.MEDIUM,
                                rule_id="YAML_007",
                                message="GitHub Actions workflow missing explicit permissions",
                                suggestion="Add explicit permissions section for security"
                            ))
                            break
        
        # Check file ending
        if lines and not content.endswith('\n'):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=len(lines),
                severity=LintSeverity.LOW,
                rule_id="YAML_008",
                message="File should end with newline",
                suggestion="Add newline at end of file",
                auto_fixable=True
            ))
        
        return issues
    
    def _check_yaml_best_practices(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check general YAML best practices"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for overly long lines
            if len(line) > 120:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="YAML_009",
                    message="Line exceeds 120 characters",
                    suggestion="Break long lines for better readability"
                ))
            
            # Check for inconsistent quotes
            if re.search(r':\s*"[^"]*"', line) and re.search(r":\s*'[^']*'", line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="YAML_010",
                    message="Inconsistent quote usage",
                    suggestion="Use consistent quote style throughout the file"
                ))
        
        return issues
    
    def _fix_issue(self, issue: LintIssue) -> bool:
        """Auto-fix specific YAML issues"""
        try:
            with open(issue.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = issue.line_number - 1
            if line_idx >= len(lines):
                return False
            
            line = lines[line_idx]
            
            if issue.rule_id == "YAML_002":  # Replace tabs with spaces
                lines[line_idx] = line.replace('\t', '  ')
                
            elif issue.rule_id == "YAML_003":  # Fix indentation to 2-space multiples
                leading_spaces = len(line) - len(line.lstrip())
                new_spaces = ((leading_spaces + 1) // 2) * 2
                lines[line_idx] = ' ' * new_spaces + line.lstrip()
                
            elif issue.rule_id == "YAML_004":  # Fix GitHub Actions steps indentation
                lines[line_idx] = '      ' + line.lstrip()  # 6 spaces
                
            elif issue.rule_id == "YAML_005":  # Remove trailing whitespace
                lines[line_idx] = line.rstrip() + '\n'
                
            elif issue.rule_id == "YAML_008":  # Add newline at end of file
                if not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
            
            else:
                return False
            
            with open(issue.file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
            
        except Exception as e:
            print(f"Error fixing {issue.file_path}: {e}")
            return False