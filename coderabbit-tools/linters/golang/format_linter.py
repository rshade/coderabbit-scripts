"""
Go format and style linter
Catches formatting issues like trailing whitespace, duplicate comments, etc.
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import GoLinter, LintIssue, LintSeverity


class FormatLinter(GoLinter):
    """Linter for Go code formatting and style issues"""
    
    def __init__(self):
        super().__init__("format")
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Check Go file for formatting issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                issues.extend(self._check_whitespace_issues(file_path, line_num, line))
                issues.extend(self._check_comment_issues(file_path, line_num, line, lines))
                issues.extend(self._check_import_issues(file_path, line_num, line))
                issues.extend(self._check_line_length(file_path, line_num, line))
            
            # Check file-level issues
            issues.extend(self._check_file_level_issues(file_path, lines))
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_whitespace_issues(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for whitespace-related issues"""
        issues = []
        
        # Trailing whitespace
        if line.rstrip() != line.rstrip('\n'):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="FMT_001",
                message="Trailing whitespace detected",
                suggestion="Remove trailing spaces and tabs",
                auto_fixable=True
            ))
        
        # Mixed tabs and spaces for indentation
        if '\t' in line and line.lstrip() != line.lstrip(' '):
            if line.startswith(' ') and '\t' in line[:len(line) - len(line.lstrip())]:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="FMT_002",
                    message="Mixed tabs and spaces for indentation",
                    suggestion="Use consistent indentation (Go standard is tabs)"
                ))
        
        # Multiple consecutive blank lines
        if line.strip() == '' and line_num > 1:
            # We'll check this in file-level issues to avoid duplicate reports
            pass
        
        return issues
    
    def _check_comment_issues(self, file_path: Path, line_num: int, line: str, all_lines: List[str]) -> List[LintIssue]:
        """Check for comment-related issues"""
        issues = []
        
        # Duplicate consecutive comments
        if line.strip().startswith('//'):
            comment_text = line.strip()[2:].strip()
            
            # Check if next line has the same comment
            if line_num < len(all_lines):
                next_line = all_lines[line_num].strip()
                if next_line.startswith('//'):
                    next_comment = next_line[2:].strip()
                    if comment_text == next_comment and comment_text:
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.LOW,
                            rule_id="FMT_003",
                            message="Duplicate consecutive comment detected",
                            suggestion="Remove duplicate comment line",
                            auto_fixable=True
                        ))
        
        # Function comments that don't start with function name
        if line.strip().startswith('// ') and line_num < len(all_lines):
            next_line = all_lines[line_num].strip()
            if next_line.startswith('func '):
                # Extract function name
                func_match = re.search(r'func\s+(?:\([^)]*\)\s+)?(\w+)', next_line)
                if func_match:
                    func_name = func_match.group(1)
                    comment_text = line.strip()[3:]  # Remove '// '
                    
                    if not comment_text.startswith(func_name):
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.LOW,
                            rule_id="FMT_004",
                            message=f"Function comment should start with function name '{func_name}'",
                            suggestion=f"Start comment with '{func_name} ...'"
                        ))
        
        return issues
    
    def _check_import_issues(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for import-related formatting issues"""
        issues = []
        
        # Single import that should be in import block
        if re.match(r'^import\s+"[^"]+"$', line.strip()):
            # This is a single import - suggest using import block for multiple imports
            # We'll only flag this if there are multiple single imports (check in file-level)
            pass
        
        # Import alias issues
        if 'import' in line and ' as ' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="FMT_005",
                message="Use Go import alias syntax (import alias \"package\")",
                suggestion="Use: import alias \"package\" instead of import \"package\" as alias"
            ))
        
        return issues
    
    def _check_line_length(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for overly long lines"""
        issues = []
        
        # Check line length (Go doesn't have strict limit, but 120 is reasonable)
        line_length = len(line.rstrip('\n'))
        if line_length > 120:
            # Ignore certain cases
            if not any(pattern in line for pattern in ['http://', 'https://', '"', '`']):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="FMT_006",
                    message=f"Line too long ({line_length} characters)",
                    suggestion="Break long lines for better readability"
                ))
        
        return issues
    
    def _check_file_level_issues(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for file-level formatting issues"""
        issues = []
        
        # Multiple consecutive blank lines
        blank_line_count = 0
        for line_num, line in enumerate(lines, 1):
            if line.strip() == '':
                blank_line_count += 1
            else:
                if blank_line_count > 2:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num - blank_line_count,
                        severity=LintSeverity.LOW,
                        rule_id="FMT_007",
                        message=f"Multiple consecutive blank lines ({blank_line_count})",
                        suggestion="Use at most 2 consecutive blank lines",
                        auto_fixable=True
                    ))
                blank_line_count = 0
        
        # File should end with newline
        if lines and not lines[-1].endswith('\n'):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=len(lines),
                severity=LintSeverity.LOW,
                rule_id="FMT_008",
                message="File should end with newline",
                suggestion="Add newline at end of file",
                auto_fixable=True
            ))
        
        # Multiple single imports that could be grouped
        single_imports = []
        for line_num, line in enumerate(lines, 1):
            if re.match(r'^import\s+"[^"]+"$', line.strip()):
                single_imports.append(line_num)
        
        if len(single_imports) > 2:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=single_imports[0],
                severity=LintSeverity.LOW,
                rule_id="FMT_009",
                message=f"Multiple single imports ({len(single_imports)}) should use import block",
                suggestion="Group imports in import ( ... ) block"
            ))
        
        return issues
    
    def _fix_issue(self, issue: LintIssue) -> bool:
        """Auto-fix formatting issues"""
        try:
            with open(issue.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            
            if issue.rule_id == "FMT_001":  # Trailing whitespace
                if issue.line_number <= len(lines):
                    line = lines[issue.line_number - 1]
                    stripped = line.rstrip() + '\n' if line.endswith('\n') else line.rstrip()
                    if line != stripped:
                        lines[issue.line_number - 1] = stripped
                        modified = True
            
            elif issue.rule_id == "FMT_003":  # Duplicate comments
                if issue.line_number <= len(lines) and issue.line_number < len(lines):
                    current_line = lines[issue.line_number - 1].strip()
                    next_line = lines[issue.line_number].strip()
                    
                    if (current_line.startswith('//') and next_line.startswith('//') and
                        current_line[2:].strip() == next_line[2:].strip()):
                        # Remove the duplicate line
                        lines.pop(issue.line_number - 1)
                        modified = True
            
            elif issue.rule_id == "FMT_007":  # Multiple consecutive blank lines
                # Find and remove excess blank lines
                new_lines = []
                blank_count = 0
                
                for line in lines:
                    if line.strip() == '':
                        blank_count += 1
                        if blank_count <= 2:  # Keep at most 2 blank lines
                            new_lines.append(line)
                    else:
                        blank_count = 0
                        new_lines.append(line)
                
                if new_lines != lines:
                    lines = new_lines
                    modified = True
            
            elif issue.rule_id == "FMT_008":  # File should end with newline
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                    modified = True
            
            if modified:
                with open(issue.file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception:
            pass
        
        return False