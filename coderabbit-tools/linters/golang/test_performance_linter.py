"""
Go test performance linter
Catches performance issues in test code like improper use of t.Parallel(), inefficient patterns, etc.
Based on CodeRabbit issues: Fix #18 (t.Parallel in fuzz), Fix #30 (build constraints), Fix #21 (test timelines)
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import GoLinter, LintIssue, LintSeverity


class TestPerformanceLinter(GoLinter):
    """Linter for test performance issues in Go code"""
    
    def __init__(self):
        super().__init__("test_performance")
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Check Go test file for performance issues"""
        issues = []
        
        # Only lint test files
        if not file_path.name.endswith('_test.go'):
            return issues
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                # Check for t.Parallel() usage issues
                issues.extend(self._check_parallel_usage(file_path, line_num, line, content))
                
                # Check for resource cleanup issues
                issues.extend(self._check_resource_cleanup(file_path, line_num, line))
                
                # Check for test timeout issues
                issues.extend(self._check_test_timeouts(file_path, line_num, line))
                
                # Check for build constraint issues
                issues.extend(self._check_build_constraints(file_path, line_num, line, lines))
                
                # Check for placeholder test issues
                issues.extend(self._check_placeholder_tests(file_path, line_num, line))
                
                # Check for sync patterns
                issues.extend(self._check_sync_patterns(file_path, line_num, line))
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_parallel_usage(self, file_path: Path, line_num: int, line: str, content: str) -> List[LintIssue]:
        """Check for improper t.Parallel() usage"""
        issues = []
        
        # Check for t.Parallel() in fuzz tests
        if 't.Parallel()' in line:
            # Check if we're in a fuzz test function
            lines = content.splitlines()
            for i in range(max(0, line_num - 10), line_num):
                if i < len(lines) and 'func Fuzz' in lines[i]:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="TESTPERF_001",
                        message="t.Parallel() should not be used in fuzz tests",
                        suggestion="Remove t.Parallel() from fuzz tests as they are resource-intensive",
                        auto_fixable=True
                    ))
                    break
        
        return issues
    
    def _check_resource_cleanup(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for proper resource cleanup in tests"""
        issues = []
        
        # Check for missing cleanup functions
        if 'sql.Open' in line or 'http.NewRequest' in line:
            if 'defer' not in line and 'cleanup' not in line.lower():
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="TESTPERF_002",
                    message="Resource created without cleanup",
                    suggestion="Use defer or t.Cleanup() to ensure resource cleanup"
                ))
        
        return issues
    
    def _check_test_timeouts(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for appropriate test timeouts"""
        issues = []
        
        # Check for very short timeouts that might cause CI failures
        if re.search(r'[1-4]\s*\*\s*time\.Second', line):
            if 'context.WithTimeout' in line or 'time.After' in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="TESTPERF_003",
                    message="Short timeout may cause test failures in CI",
                    suggestion="Use 15s timeout for database/external service tests to handle CI latency"
                ))
        
        # Recommend specific timeout for database tests
        if 'mysql' in line.lower() or 'database' in line.lower():
            if re.search(r'[1-9]\s*\*\s*time\.Second', line) and not re.search(r'1[5-9]\s*\*\s*time\.Second', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="TESTPERF_004",
                    message="Database test timeout should be 15s for CI reliability",
                    suggestion="Use 15 * time.Second for database connection timeouts in tests"
                ))
        
        return issues
    
    def _check_build_constraints(self, file_path: Path, line_num: int, line: str, lines: List[str]) -> List[LintIssue]:
        """Check for proper build constraints in test files"""
        issues = []
        
        # Check if file has both modern and legacy build constraints
        if line_num <= 3:  # Only check top of file
            has_modern = any('//go:build' in l for l in lines[:5])
            has_legacy = any('// +build' in l for l in lines[:5])
            
            if has_modern and not has_legacy:
                if '//go:build' in line:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.LOW,
                        rule_id="TESTPERF_005",
                        message="Modern build constraint without legacy fallback",
                        suggestion="Add legacy // +build constraint for backward compatibility"
                    ))
        
        # Check for placeholder tests without build constraints
        if 'TestPlaceholder' in line or 't.Skip(' in line:
            # Check if file has integration exclusion
            has_integration_exclusion = any('!integration' in l for l in lines[:5])
            if not has_integration_exclusion:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="TESTPERF_006",
                    message="Placeholder test without build constraints",
                    suggestion="Add //go:build !integration constraint to exclude from integration tests"
                ))
        
        return issues
    
    def _check_placeholder_tests(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for placeholder test patterns"""
        issues = []
        
        # Check for placeholder tests without timelines
        if 't.Skip(' in line and 'placeholder' in line.lower():
            if 'TODO' not in line and 'timeline' not in line.lower():
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="TESTPERF_007",
                    message="Placeholder test without implementation timeline",
                    suggestion="Add TODO comment with completion timeline for placeholder tests"
                ))
        
        # Check for placeholder tests that should be changed to t.FailNow()
        if 't.Skip(' in line and re.search(r'20(2[5-9]|[3-9]\d)', line):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="TESTPERF_008",
                message="Placeholder test past implementation deadline",
                suggestion="Change t.Skip() to t.FailNow() for overdue placeholder tests"
            ))
        
        return issues
    
    def _check_sync_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for proper synchronization patterns in tests"""
        issues = []
        
        # Check for proper WaitGroup usage over error channels
        if 'make(chan error' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="TESTPERF_009",
                message="Error channel for synchronization",
                suggestion="Consider using sync.WaitGroup for more robust goroutine coordination"
            ))
        
        # Check for concurrent slice append without mutex
        if 'append(' in line and 'go func' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.HIGH,
                rule_id="TESTPERF_010",
                message="Concurrent slice append without synchronization",
                suggestion="Use sync.Mutex to protect concurrent slice appends"
            ))
        
        return issues
    
    def _fix_issue(self, issue: LintIssue) -> bool:
        """Auto-fix specific test performance issues"""
        if issue.rule_id == "TESTPERF_001":  # Remove t.Parallel() from fuzz tests
            try:
                with open(issue.file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                line = lines[issue.line_number - 1]
                if 't.Parallel()' in line:
                    # Remove the entire line if it only contains t.Parallel()
                    if line.strip() == 't.Parallel()':
                        lines.pop(issue.line_number - 1)
                    else:
                        # Remove just the t.Parallel() call
                        lines[issue.line_number - 1] = line.replace('t.Parallel()', '').strip() + '\n'
                    
                    with open(issue.file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    return True
                        
            except Exception as e:
                print(f"Error fixing {issue.file_path}: {e}")
        
        return False