"""
Go Unicode and String Handling Linter
Catches issues with string length counting, case sensitivity, and text processing
Based on CodeRabbit issues: Fix #16 (unicode counting), Fix #17 (case-insensitive validation)
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import GoLinter, LintIssue, LintSeverity


class UnicodeStringLinter(GoLinter):
    """Linter for Unicode and string handling issues in Go code"""
    
    def __init__(self):
        super().__init__("unicode_string")
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Check Go file for Unicode and string handling issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # Check for incorrect string length counting
                issues.extend(self._check_string_length_counting(file_path, line_num, line))
                
                # Check for case-insensitive string comparisons
                issues.extend(self._check_case_insensitive_comparisons(file_path, line_num, line))
                
                # Check for proper Unicode normalization
                issues.extend(self._check_unicode_normalization(file_path, line_num, line))
                
                # Check for string validation patterns
                issues.extend(self._check_string_validation_patterns(file_path, line_num, line))
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_string_length_counting(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for byte vs character counting issues"""
        issues = []
        
        # Check for len() used on strings in validation contexts
        if re.search(r'len\([^)]*string[^)]*\)\s*[<>]=?\s*\d+', line):
            # Look for validation context keywords
            validation_keywords = ['validate', 'check', 'length', 'max', 'min', 'limit']
            if any(keyword in line.lower() for keyword in validation_keywords):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="UNICODE_001",
                    message="Using len() for string validation counts bytes, not Unicode characters",
                    suggestion="Use utf8.RuneCountInString() for character count validation",
                    auto_fixable=True
                ))
        
        # Check for hardcoded byte-based length checks
        if re.search(r'len\([^)]*\)\s*>\s*\d{2,}', line) and 'string' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="UNICODE_002",
                message="String length check may not handle Unicode correctly",
                suggestion="Consider using utf8.RuneCountInString() if Unicode support is needed"
            ))
        
        return issues
    
    def _check_case_insensitive_comparisons(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for missing case-insensitive string comparisons"""
        issues = []
        
        # Check for string equality comparisons that should be case-insensitive
        enum_patterns = [
            r'condition\s*==\s*["\'][^"\']*["\']',
            r'["\'][^"\']*["\']\s*==\s*condition',
            r'status\s*==\s*["\'][^"\']*["\']',
            r'["\'][^"\']*["\']\s*==\s*status',
            r'type\s*==\s*["\'][^"\']*["\']',
            r'["\'][^"\']*["\']\s*==\s*type'
        ]
        
        for pattern in enum_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Check if strings.ToLower or strings.EqualFold is not used
                if 'strings.ToLower' not in line and 'strings.EqualFold' not in line:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="UNICODE_003",
                        message="String comparison should be case-insensitive for enum-like values",
                        suggestion="Use strings.EqualFold() or strings.ToLower() for case-insensitive comparison"
                    ))
        
        return issues
    
    def _check_unicode_normalization(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for Unicode normalization issues"""
        issues = []
        
        # Check for user input validation without normalization
        if re.search(r'(name|email|username|title|description).*validate', line, re.IGNORECASE):
            if 'norm' not in line.lower() and 'unicode' not in line.lower():
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="UNICODE_004",
                    message="User input validation may need Unicode normalization",
                    suggestion="Consider using golang.org/x/text/unicode/norm for consistent text processing"
                ))
        
        return issues
    
    def _check_string_validation_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for common string validation anti-patterns"""
        issues = []
        
        # Check for hardcoded magic numbers in string validation
        if re.search(r'len\([^)]+\)\s*[<>]=?\s*(50|100|200|255|500|1000|2000)', line):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="UNICODE_005",
                message="Hardcoded string length limit found",
                suggestion="Define string length constants with descriptive names"
            ))
        
        # Check for missing UTF-8 validity checks
        if re.search(r'string.*validate', line, re.IGNORECASE) and 'utf8.Valid' not in line:
            if 'user' in line.lower() or 'input' in line.lower():
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="UNICODE_006",
                    message="User input validation should check UTF-8 validity",
                    suggestion="Use utf8.ValidString() to ensure valid UTF-8 encoding"
                ))
        
        return issues
    
    def _fix_issue(self, issue: LintIssue) -> bool:
        """Auto-fix specific Unicode issues"""
        if issue.rule_id == "UNICODE_001":
            try:
                with open(issue.file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                line = lines[issue.line_number - 1]
                # Replace len(string) with utf8.RuneCountInString(string) in validation contexts
                fixed_line = re.sub(
                    r'len\(([^)]*string[^)]*)\)',
                    r'utf8.RuneCountInString(\1)',
                    line
                )
                
                if fixed_line != line:
                    lines[issue.line_number - 1] = fixed_line
                    
                    with open(issue.file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    return True
                        
            except Exception as e:
                print(f"Error fixing {issue.file_path}: {e}")
        
        return False