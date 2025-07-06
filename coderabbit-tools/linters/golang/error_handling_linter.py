"""
Go error handling linter
Catches issues with error wrapping, sentinel errors, and error patterns
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import GoLinter, LintIssue, LintSeverity


class ErrorHandlingLinter(GoLinter):
    """Linter for Go error handling patterns"""
    
    def __init__(self):
        super().__init__("error_handling")
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Check Go file for error handling issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                issues.extend(self._check_error_wrapping(file_path, line_num, line))
                issues.extend(self._check_sentinel_errors(file_path, line_num, line))
                issues.extend(self._check_error_creation(file_path, line_num, line))
                issues.extend(self._check_error_handling(file_path, line_num, line))
                
            # Check file-level error patterns
            issues.extend(self._check_error_definitions(file_path, content))
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_error_wrapping(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for proper error wrapping patterns"""
        issues = []
        
        # fmt.Errorf without %w verb for error wrapping
        if 'fmt.Errorf(' in line and '%w' not in line and 'err' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="ERR_001",
                message="fmt.Errorf without %w verb - error chain may be lost",
                suggestion="Use %w verb to wrap errors: fmt.Errorf(\"context: %w\", err)",
                auto_fixable=False
            ))
        
        # Double error wrapping (fmt.Errorf with multiple %w) - but allow sentinel + custom error pattern
        if 'fmt.Errorf(' in line and line.count('%w') > 1:
            # Allow the pattern: fmt.Errorf("%w: %w", ErrSentinel, &CustomError{})
            if not ('Err' in line and '&' in line and 'Error{' in line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="ERR_002",
                    message="Multiple %w verbs in single fmt.Errorf call",
                    suggestion="Use only one %w verb per fmt.Errorf call "
                              "(unless using sentinel + custom error pattern)",
                    auto_fixable=False
                ))
        
        # errors.New when should wrap existing error
        if 'errors.New(' in line and 'err' in line and 'fmt.Errorf' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="ERR_003",
                message="errors.New() when error wrapping might be needed",
                suggestion="Consider using fmt.Errorf(\"%w\", err) to preserve error chain",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_sentinel_errors(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for sentinel error patterns"""
        issues = []
        
        # Sentinel error definition patterns
        if re.match(r'var\s+Err\w+\s*=\s*errors\.New', line):
            # Good sentinel error pattern
            pass
        elif 'var Err' in line and '=' in line and 'errors.New' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="ERR_004",
                message="Sentinel error should use errors.New()",
                suggestion="Define sentinel errors with: var ErrName = errors.New(\"description\")",
                auto_fixable=False
            ))
        
        # Direct struct error return without sentinel wrapping
        if re.search(r'return.*&\w+Error{.*}', line) and 'fmt.Errorf' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="ERR_005",
                message="Direct error struct return without sentinel error wrapping",
                suggestion="Wrap with sentinel error: fmt.Errorf(\"%w: %w\", ErrSentinel, &CustomError{})",
                auto_fixable=False
            ))
        
        # errors.Is usage with wrong pattern
        if 'errors.Is(' in line and '&' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.HIGH,
                rule_id="ERR_006",
                message="errors.Is() with pointer - should use value",
                suggestion="Use errors.Is(err, ErrSentinel) not errors.Is(err, &structError{})",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_error_creation(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for error creation patterns"""
        issues = []
        
        # Error struct without Error() method
        if re.match(r'type\s+\w+Error\s+struct', line):
            # This would need multi-line analysis to check for Error() method
            # For now, just suggest it
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="ERR_007",
                message="Custom error type should implement Error() method",
                suggestion="Implement func (e *CustomError) Error() string method",
                auto_fixable=False
            ))
        
        # Panic instead of proper error return
        if 'panic(' in line and file_path.name != 'main.go' and '_test.go' not in file_path.name:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.HIGH,
                rule_id="ERR_008",
                message="panic() used instead of proper error handling",
                suggestion="Return error instead of panicking for recoverable conditions",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_error_handling(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for error handling patterns"""
        issues = []
        
        # Ignored error without comment
        if '_ = ' in line and '(' in line and ')' in line and 'nolint' not in line:
            # Likely ignoring an error return
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="ERR_009",
                message="Ignored error without explanation comment",
                suggestion="Add //nolint:errcheck // reason comment or handle the error",
                auto_fixable=True
            ))
        
        # Error assignment without handling
        if re.search(r'(\w+)\s*,\s*err\s*:?=', line) and 'if err' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="ERR_010",
                message="Error variable assigned but not checked",
                suggestion="Add error handling: if err != nil { return err }",
                auto_fixable=False
            ))
        
        # Generic error messages without context
        if 'return err' in line and 'fmt.Errorf' not in line and 'errors.New' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="ERR_011",
                message="Returning error without additional context",
                suggestion="Add context with fmt.Errorf(\"operation failed: %w\", err)",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_error_definitions(self, file_path: Path, content: str) -> List[LintIssue]:
        """Check file-level error definition patterns"""
        issues = []
        
        # Missing sentinel error for custom error types
        lines = content.splitlines()
        has_custom_errors = False
        has_sentinel_errors = False
        
        for line in lines:
            if re.search(r'type\s+\w+Error\s+struct', line):
                has_custom_errors = True
            if re.search(r'var\s+Err\w+\s*=\s*errors\.New', line):
                has_sentinel_errors = True
        
        if has_custom_errors and not has_sentinel_errors:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=1,
                severity=LintSeverity.MEDIUM,
                rule_id="ERR_012",
                message="Custom error types without corresponding sentinel errors",
                suggestion="Define sentinel errors for custom error types for easier error checking",
                auto_fixable=False
            ))
        
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
            
            # Fix ignored error without comment
            if issue.rule_id == "ERR_009":
                if '_ = ' in line and 'nolint' not in line:
                    # Add nolint comment
                    line = line.rstrip() + ' //nolint:errcheck // intentionally ignored\n'
                    lines[line_idx] = line
                    
                    with open(issue.file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    return True
                    
        except Exception as e:
            print(f"Error auto-fixing {issue.file_path}:{issue.line_number}: {e}")
            
        return False