"""
Markdown linter that integrates with markdownlint-cli
"""

import json
import subprocess
import shutil
from pathlib import Path
from typing import List

from ..base_linter import MarkdownLinter, LintIssue, LintSeverity


class MarkdownLintLinter(MarkdownLinter):
    """Linter that runs markdownlint on markdown files"""
    
    def __init__(self):
        super().__init__("markdownlint")
        self.markdownlint_available = self._check_markdownlint_available()
    
    def _check_markdownlint_available(self) -> bool:
        """Check if markdownlint-cli is installed"""
        return shutil.which('markdownlint') is not None
    
    def lint(self, project_path: Path) -> List[LintIssue]:
        """Run markdownlint on all markdown files"""
        if not self.markdownlint_available:
            print("Warning: markdownlint-cli not found. Install with: npm install -g markdownlint-cli")
            return []
        
        all_issues = []
        
        # Find all markdown files
        markdown_files = []
        for pattern in self.file_patterns:
            for file_path in project_path.rglob(pattern):
                if not self._should_skip_file(file_path):
                    markdown_files.append(file_path)
        
        if not markdown_files:
            return []
        
        # Run markdownlint
        try:
            # Use --json flag for structured output
            cmd = ['markdownlint', '--json'] + [str(f) for f in markdown_files]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)
            
            if result.stdout:
                # Parse JSON output
                try:
                    lint_results = json.loads(result.stdout)
                    # Validate that lint_results is a proper dictionary
                    if isinstance(lint_results, dict):
                        all_issues.extend(self._parse_markdownlint_output(lint_results, project_path))
                    else:
                        # If not a dict, try parsing stderr instead
                        all_issues.extend(self._parse_markdownlint_stderr(result.stderr, project_path))
                except json.JSONDecodeError:
                    # Fallback to stderr parsing if JSON failed
                    all_issues.extend(self._parse_markdownlint_stderr(result.stderr, project_path))
            elif result.stderr:
                # Parse stderr output (non-JSON format)
                all_issues.extend(self._parse_markdownlint_stderr(result.stderr, project_path))
                
        except subprocess.SubprocessError as e:
            print(f"Error running markdownlint: {e}")
        
        return all_issues
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint a single markdown file"""
        if not self.markdownlint_available:
            return []
        
        try:
            cmd = ['markdownlint', '--json', str(file_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.stdout:
                try:
                    lint_results = json.loads(result.stdout)
                    return self._parse_markdownlint_output(lint_results, file_path.parent)
                except json.JSONDecodeError:
                    return self._parse_markdownlint_stderr(result.stderr, file_path.parent)
            elif result.stderr:
                return self._parse_markdownlint_stderr(result.stderr, file_path.parent)
                
        except subprocess.SubprocessError:
            pass
        
        return []
    
    def _parse_markdownlint_output(self, lint_results: dict, project_path: Path) -> List[LintIssue]:
        """Parse JSON output from markdownlint"""
        issues = []
        
        for file_path_str, file_issues in lint_results.items():
            # Skip if file_issues is not a list (could be malformed JSON)
            if not isinstance(file_issues, list):
                continue
            
            # Validate that file_path_str looks like a valid file path
            if not file_path_str or file_path_str.startswith('"') or not Path(file_path_str).suffix:
                continue
                
            file_path = Path(file_path_str)
            
            for issue in file_issues:
                # Skip if issue is not a dictionary
                if not isinstance(issue, dict):
                    continue
                
                # Ensure required fields exist
                if 'lineNumber' not in issue and 'ruleNames' not in issue:
                    continue
                    
                line_number = issue.get('lineNumber', 1)
                rule_names = issue.get('ruleNames', [])
                rule_id = rule_names[0] if rule_names else 'unknown'
                description = issue.get('ruleDescription', 'Markdown style issue')
                detail = issue.get('errorDetail', '')
                
                message = description
                if detail:
                    message += f": {detail}"
                
                # Map rule severity
                severity = self._map_rule_severity(rule_id)
                
                suggestion = self._get_rule_suggestion(rule_id, issue)
                
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_number,
                    severity=severity,
                    rule_id=rule_id,
                    message=message,
                    suggestion=suggestion,
                    auto_fixable=rule_id in ['MD047', 'MD012', 'MD010']  # Some auto-fixable rules
                ))
        
        return issues
    
    def _parse_markdownlint_stderr(self, stderr: str, project_path: Path) -> List[LintIssue]:
        """Parse text output from markdownlint stderr"""
        issues = []
        
        for line in stderr.strip().split('\n'):
            if not line.strip():
                continue
                
            # Format: filename:line_number rule_id description
            parts = line.split(':', 3)
            if len(parts) >= 3:
                file_path = Path(parts[0])
                try:
                    line_number = int(parts[1])
                except ValueError:
                    line_number = 1
                
                rule_and_desc = parts[2] if len(parts) > 2 else 'unknown issue'
                rule_parts = rule_and_desc.strip().split(' ', 1)
                rule_id = rule_parts[0] if rule_parts else 'unknown'
                message = rule_parts[1] if len(rule_parts) > 1 else 'Markdown issue'
                
                severity = self._map_rule_severity(rule_id)
                suggestion = self._get_rule_suggestion(rule_id, {})
                
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_number,
                    severity=severity,
                    rule_id=rule_id,
                    message=message,
                    suggestion=suggestion
                ))
        
        return issues
    
    def _map_rule_severity(self, rule_id: str) -> LintSeverity:
        """Map markdownlint rule IDs to severity levels"""
        # High priority: structural issues that affect readability
        high_priority_rules = {
            'MD001',  # Header levels increment by one
            'MD003',  # Header style consistency
            'MD022',  # Headers surrounded by blank lines
            'MD025',  # Multiple top-level headers
            'MD026',  # Trailing punctuation in headers
        }
        
        # Medium priority: formatting and consistency
        medium_priority_rules = {
            'MD004',  # Unordered list style
            'MD005',  # Inconsistent indentation for list items
            'MD007',  # Unordered list indentation
            'MD009',  # Trailing spaces
            'MD010',  # Hard tabs
            'MD011',  # Reversed link syntax
            'MD012',  # Multiple consecutive blank lines
            'MD013',  # Line length
            'MD018',  # No space after hash on atx style header
            'MD019',  # Multiple spaces after hash on atx style header
            'MD023',  # Headers must start at the beginning of the line
            'MD029',  # Ordered list item prefix
            'MD030',  # Spaces after list markers
            'MD032',  # Lists should be surrounded by blank lines
            'MD034',  # Bare URLs used
            'MD037',  # Spaces inside emphasis markers
            'MD038',  # Spaces inside code span elements
            'MD039',  # Spaces inside link text
            'MD040',  # Fenced code blocks should have a language specified
            'MD046',  # Code block style
            'MD047',  # Files should end with a single newline character
        }
        
        if rule_id in high_priority_rules:
            return LintSeverity.HIGH
        elif rule_id in medium_priority_rules:
            return LintSeverity.MEDIUM
        else:
            return LintSeverity.LOW
    
    def _get_rule_suggestion(self, rule_id: str, issue: dict) -> str:
        """Get specific suggestions for common markdownlint rules"""
        suggestions = {
            'MD001': 'Use incremental header levels (# then ## then ###)',
            'MD003': 'Use consistent header style throughout the document',
            'MD004': 'Use consistent marker for unordered lists (* or - or +)',
            'MD009': 'Remove trailing spaces from lines',
            'MD010': 'Replace hard tabs with spaces',
            'MD012': 'Remove multiple consecutive blank lines',
            'MD013': 'Break long lines or increase line length limit',
            'MD022': 'Add blank lines around headers',
            'MD025': 'Use only one top-level header per document',
            'MD034': 'Use link syntax [text](url) instead of bare URLs',
            'MD040': 'Add language identifier to fenced code blocks',
            'MD047': 'Add single newline at end of file',
        }
        
        return suggestions.get(rule_id, 'Check markdownlint documentation for details')
    
    def _fix_issue(self, issue: LintIssue) -> bool:
        """Auto-fix certain markdown issues"""
        if not issue.auto_fixable:
            return False
        
        try:
            with open(issue.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if issue.rule_id == 'MD047':  # File should end with newline
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                    with open(issue.file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    return True
            
            elif issue.rule_id == 'MD012':  # Multiple consecutive blank lines
                # Remove extra blank lines
                new_lines = []
                prev_blank = False
                for line in lines:
                    is_blank = line.strip() == ''
                    if not (is_blank and prev_blank):
                        new_lines.append(line)
                    prev_blank = is_blank
                
                if new_lines != lines:
                    with open(issue.file_path, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                    return True
            
            elif issue.rule_id == 'MD010':  # Hard tabs
                new_lines = [line.replace('\t', '    ') for line in lines]
                if new_lines != lines:
                    with open(issue.file_path, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                    return True
                    
        except Exception:
            pass
        
        return False