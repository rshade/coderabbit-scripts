"""
YAML linter for Node.js projects
Catches issues in CI/CD files, config files, etc.
"""

import re
import yaml
import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

from ..base_linter import NodeJSLinter, LintIssue, LintSeverity


class YamlLinter(NodeJSLinter):
    """Linter for YAML files in Node.js projects"""
    
    def __init__(self):
        super().__init__("yaml", ["*.yml", "*.yaml", ".github/workflows/*.yml", ".github/workflows/*.yaml"])
        self._ensure_yamllint_installed()
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint YAML files using yamllint and custom checks"""
        issues = []
        
        # First, run yamllint
        yamllint_issues = self._run_yamllint(file_path)
        issues.extend(yamllint_issues)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Only run custom checks if YAML syntax is valid
            try:
                yaml.safe_load(content)
                # Add custom checks that yamllint doesn't cover
                for line_num, line in enumerate(lines, 1):
                    issues.extend(self._check_github_actions(file_path, line_num, line))
                
            except yaml.YAMLError as e:
                # yamllint should have caught this, but just in case
                line_num = getattr(e, 'problem_mark', None)
                line_num = line_num.line + 1 if line_num else 1
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="YAML_001",
                    message=f"YAML syntax error: {e}",
                    suggestion="Fix YAML syntax"
                ))
                
        except Exception as e:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=1,
                severity=LintSeverity.HIGH,
                rule_id="YAML_002",
                message=f"Error reading YAML file: {e}",
                suggestion="Check file encoding and permissions"
            ))
        
        return issues
    
    def _ensure_yamllint_installed(self) -> bool:
        """Ensure yamllint is installed, install if necessary"""
        try:
            subprocess.run(['yamllint', '--version'], 
                         capture_output=True, check=True, timeout=10)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("yamllint not found, installing...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'yamllint>=1.35.0'], 
                             check=True, timeout=60)
                print("yamllint installed successfully")
                return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f"Failed to install yamllint: {e}")
                return False
    
    def _run_yamllint(self, file_path: Path) -> List[LintIssue]:
        """Run yamllint on a file and convert output to LintIssue objects"""
        issues = []
        
        try:
            # Run yamllint with JSON output format
            result = subprocess.run([
                'yamllint', 
                '--format', 'parsable',
                str(file_path)
            ], capture_output=True, text=True, timeout=30)
            
            # yamllint exits with non-zero code when issues are found, which is expected
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        issue = self._parse_yamllint_line(file_path, line)
                        if issue:
                            issues.append(issue)
                            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            # If yamllint fails, add a warning but continue with custom checks
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=1,
                severity=LintSeverity.LOW,
                rule_id="YAML_YAMLLINT_ERROR",
                message=f"yamllint execution failed: {e}",
                suggestion="Check yamllint installation or file permissions"
            ))
        
        return issues
    
    def _parse_yamllint_line(self, file_path: Path, line: str) -> LintIssue:
        """Parse a yamllint output line into a LintIssue"""
        try:
            # yamllint parsable format: file:line:column: [level] message (rule)
            parts = line.split(':', 3)
            if len(parts) < 4:
                return None
                
            line_num = int(parts[1])
            col_num = int(parts[2])
            
            # Extract level and message
            remainder = parts[3].strip()
            if remainder.startswith('['):
                level_end = remainder.find(']')
                level = remainder[1:level_end].strip()
                message_part = remainder[level_end + 1:].strip()
            else:
                level = 'error'
                message_part = remainder
            
            # Extract rule from message (rule)
            rule_id = "YAMLLINT_GENERIC"
            if '(' in message_part and message_part.endswith(')'):
                rule_start = message_part.rfind('(')
                rule_id = f"YAMLLINT_{message_part[rule_start+1:-1].upper().replace('-', '_')}"
                message = message_part[:rule_start].strip()
            else:
                message = message_part
            
            # Map yamllint levels to our severity levels
            severity_map = {
                'error': LintSeverity.HIGH,
                'warning': LintSeverity.MEDIUM,
                'info': LintSeverity.LOW
            }
            severity = severity_map.get(level.lower(), LintSeverity.MEDIUM)
            
            # Determine if this is auto-fixable
            auto_fixable = rule_id in [
                'YAMLLINT_TRAILING_SPACES',
                'YAMLLINT_NEW_LINE_AT_END_OF_FILE',
                'YAMLLINT_TOO_MANY_BLANK_LINES'
            ]
            
            return self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=severity,
                rule_id=rule_id,
                message=f"{message} (col {col_num})",
                suggestion=f"Fix {rule_id.lower().replace('yamllint_', '').replace('_', ' ')}",
                auto_fixable=auto_fixable
            )
            
        except (ValueError, IndexError) as e:
            # If we can't parse the line, create a generic issue
            return self._create_issue(
                file_path=file_path,
                line_number=1,
                severity=LintSeverity.LOW,
                rule_id="YAML_PARSE_ERROR",
                message=f"Could not parse yamllint output: {line}",
                suggestion="Check yamllint output format"
            )
    
    def _check_formatting(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check YAML formatting issues (reduced set since yamllint handles most formatting)"""
        issues = []
        
        # Most formatting issues are now handled by yamllint
        # Keep this method for any future custom formatting checks
        
        return issues
    
    def _check_github_actions(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check GitHub Actions specific issues"""
        issues = []
        
        # Only check files in .github/workflows/
        if '.github/workflows' not in str(file_path):
            return issues
        
        # Check for outdated action versions
        action_patterns = {
            r'uses:\s*actions/checkout@v[12]': 'actions/checkout@v4',
            r'uses:\s*actions/setup-node@v[12]': 'actions/setup-node@v4',
            r'uses:\s*actions/cache@v[12]': 'actions/cache@v4',
        }
        
        for pattern, suggestion in action_patterns.items():
            if re.search(pattern, line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="YAML_006",
                    message="Outdated GitHub Action version",
                    suggestion=f"Update to {suggestion}"
                ))
        
        # Check for missing node version matrix
        if 'strategy:' in line and 'node' in str(file_path).lower():
            # This is a heuristic - we should check if matrix includes multiple node versions
            pass
        
        # Check for secrets in plain text
        if re.search(r'(password|token|key|secret):\s*[^$]', line, re.IGNORECASE):
            if not re.search(r'\$\{\{\s*secrets\.', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="YAML_007",
                    message="Potential hardcoded secret in GitHub Actions",
                    suggestion="Use ${{ secrets.SECRET_NAME }} for sensitive values"
                ))
        
        return issues
    
    def _check_file_level(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check file-level YAML issues (reduced since yamllint handles most)"""
        issues = []
        
        # Most file-level issues are now handled by yamllint
        # Keep this method for any future custom file-level checks
        
        return issues
    
    def _fix_issue(self, issue: LintIssue) -> bool:
        """Auto-fix YAML formatting issues (yamllint-aware)"""
        try:
            with open(issue.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            
            # Handle yamllint-specific rule IDs
            if issue.rule_id == "YAMLLINT_TRAILING_SPACES":
                if issue.line_number <= len(lines):
                    line = lines[issue.line_number - 1]
                    stripped = line.rstrip() + '\n' if line.endswith('\n') else line.rstrip()
                    if line != stripped:
                        lines[issue.line_number - 1] = stripped
                        modified = True
            
            elif issue.rule_id == "YAMLLINT_NEW_LINE_AT_END_OF_FILE":
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                    modified = True
            
            elif issue.rule_id == "YAMLLINT_TOO_MANY_BLANK_LINES":
                new_lines = []
                blank_count = 0
                
                for line in lines:
                    if line.strip() == '':
                        blank_count += 1
                        if blank_count <= 2:
                            new_lines.append(line)
                    else:
                        blank_count = 0
                        new_lines.append(line)
                
                if new_lines != lines:
                    lines = new_lines
                    modified = True
            
            # Legacy rule IDs (for backward compatibility)
            elif issue.rule_id == "YAML_003":  # Trailing whitespace
                if issue.line_number <= len(lines):
                    line = lines[issue.line_number - 1]
                    stripped = line.rstrip() + '\n' if line.endswith('\n') else line.rstrip()
                    if line != stripped:
                        lines[issue.line_number - 1] = stripped
                        modified = True
            
            elif issue.rule_id == "YAML_004":  # Tabs to spaces
                if issue.line_number <= len(lines):
                    line = lines[issue.line_number - 1]
                    new_line = line.replace('\t', '  ')  # Replace tabs with 2 spaces
                    if line != new_line:
                        lines[issue.line_number - 1] = new_line
                        modified = True
            
            if modified:
                with open(issue.file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception:
            pass
        
        return False