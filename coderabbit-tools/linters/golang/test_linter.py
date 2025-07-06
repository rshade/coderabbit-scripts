"""
Go test linter
Catches issues with test patterns, concurrency, and best practices
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import GoLinter, LintIssue, LintSeverity


class TestLinter(GoLinter):
    """Linter for Go test files and testing patterns"""
    
    def __init__(self):
        super().__init__("test")
        self.file_patterns = ["*_test.go"]
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Check Go test file for testing issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                issues.extend(self._check_test_patterns(file_path, line_num, line))
                issues.extend(self._check_test_concurrency(file_path, line_num, line))
                issues.extend(self._check_test_assertions(file_path, line_num, line))
            
            # Check file-level test issues
            issues.extend(self._check_test_file_structure(file_path, content))
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_test_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for Go test pattern issues"""
        issues = []
        
        # Test function naming
        if re.match(r'func\s+Test\w+', line):
            func_match = re.search(r'func\s+(Test\w+)', line)
            if func_match:
                func_name = func_match.group(1)
                # Check if test function has proper signature
                if '(t *testing.T)' not in line:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="TEST_001",
                        message=f"Test function '{func_name}' should have signature (t *testing.T)",
                        suggestion="Change signature to func TestName(t *testing.T)"
                    ))
        
        # Benchmark function naming
        if re.match(r'func\s+Benchmark\w+', line):
            if '(b *testing.B)' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="TEST_002",
                    message="Benchmark function should have signature (b *testing.B)",
                    suggestion="Change signature to func BenchmarkName(b *testing.B)"
                ))
        
        # Fuzz function naming  
        if re.match(r'func\s+Fuzz\w+', line):
            if '(f *testing.F)' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="TEST_003",
                    message="Fuzz function should have signature (f *testing.F)",
                    suggestion="Change signature to func FuzzName(f *testing.F)"
                ))
        
        return issues
    
    def _check_test_concurrency(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for test concurrency issues"""
        issues = []
        
        # Check for t.Parallel() in fuzz tests
        if 't.Parallel()' in line:
            # Look for fuzz test context (this is a heuristic)
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="TEST_004",
                message="t.Parallel() may cause issues in fuzz tests",
                suggestion="Remove t.Parallel() from fuzz tests as fuzzing engine handles concurrency"
            ))
        
        # Check for goroutines in tests without proper synchronization
        if 'go func(' in line and 'WaitGroup' not in line and 'channel' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="TEST_005",
                message="Goroutine in test without synchronization mechanism",
                suggestion="Use sync.WaitGroup or channels to synchronize goroutines in tests"
            ))
        
        # Check for error channels that might cause deadlocks
        if 'make(chan error' in line and 'buffered' not in line.lower():
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="TEST_006",
                message="Unbuffered error channel may cause deadlock in tests",
                suggestion="Use buffered channel or sync.WaitGroup for better test reliability"
            ))
        
        return issues
    
    def _check_test_assertions(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for test assertion patterns"""
        issues = []
        
        # Check for missing error handling in tests
        if '= ' in line and 'err' in line and 'if err != nil' not in line:
            # Look for function calls that return error
            if re.search(r'(\w+)\s*,\s*err\s*:?=', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="TEST_007",
                    message="Error return value not checked in test",
                    suggestion="Add error checking: if err != nil { t.Fatal(err) }"
                ))
        
        # Check for t.Error vs t.Fatal usage
        if 't.Error(' in line and 'return' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="TEST_008",
                message="Consider using t.Fatal() instead of t.Error() if test cannot continue",
                suggestion="Use t.Fatal() for critical errors that should stop test execution"
            ))
        
        # Check for hardcoded test data
        if re.search(r'["\'](?:test|mock|fake|dummy)["\']', line, re.IGNORECASE):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="TEST_009",
                message="Consider using more descriptive test data",
                suggestion="Use realistic test data that reflects actual use cases"
            ))
        
        return issues
    
    def _check_test_file_structure(self, file_path: Path, content: str) -> List[LintIssue]:
        """Check test file structure and organization"""
        issues = []
        
        # Check for missing test functions
        if 'func Test' not in content and 'func Benchmark' not in content and 'func Fuzz' not in content:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=1,
                severity=LintSeverity.MEDIUM,
                rule_id="TEST_010",
                message="Test file contains no test functions",
                suggestion="Add test functions with Test, Benchmark, or Fuzz prefix"
            ))
        
        # Check for missing package declaration
        if not content.startswith('package '):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=1,
                severity=LintSeverity.HIGH,
                rule_id="TEST_011",
                message="Test file missing package declaration",
                suggestion="Add package declaration at top of file"
            ))
        
        # Check for missing testing import
        if 'func Test' in content and '"testing"' not in content:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=1,
                severity=LintSeverity.HIGH,
                rule_id="TEST_012",
                message="Test file missing testing package import",
                suggestion="Add import \"testing\" to use testing functions"
            ))
        
        # Check for very long test functions (>100 lines)
        lines = content.splitlines()
        in_test_func = False
        test_start_line = 0
        test_name = ""
        
        for line_num, line in enumerate(lines, 1):
            if re.match(r'func\s+(Test\w+|Benchmark\w+|Fuzz\w+)', line):
                in_test_func = True
                test_start_line = line_num
                match = re.search(r'func\s+(Test\w+|Benchmark\w+|Fuzz\w+)', line)
                test_name = match.group(1) if match else "unknown"
            elif in_test_func and (line.startswith('func ') or line_num == len(lines)):
                # End of function
                func_length = line_num - test_start_line
                if func_length > 100:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=test_start_line,
                        severity=LintSeverity.LOW,
                        rule_id="TEST_013",
                        message=f"Test function '{test_name}' is very long ({func_length} lines)",
                        suggestion="Consider breaking down into smaller test functions or helper functions"
                    ))
                in_test_func = False
        
        return issues