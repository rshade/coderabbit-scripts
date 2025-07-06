"""
Go context handling linter
Catches issues with context cancellation, timeouts, and proper propagation
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import GoLinter, LintIssue, LintSeverity


class ContextLinter(GoLinter):
    """Linter for Go context handling patterns"""
    
    def __init__(self):
        super().__init__("context")
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Check Go file for context handling issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Check each line for context issues
            for line_num, line in enumerate(lines, 1):
                issues.extend(self._check_context_cancellation(file_path, line_num, line))
                issues.extend(self._check_context_timeout(file_path, line_num, line))
                issues.extend(self._check_context_propagation(file_path, line_num, line))
            
            # Check function signatures
            issues.extend(self._check_function_signatures(file_path, content))
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_context_cancellation(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for proper context cancellation handling"""
        issues = []
        
        # Check for missing ctx.Err() checks in long-running operations
        if 'func ' in line and 'ctx context.Context' in line:
            # This is a function that takes context - we'll flag if it doesn't check ctx.Err()
            # This is a heuristic check; more sophisticated analysis would look at the function body
            pass
        
        # Check for ctx.Err() checks in specific patterns
        if re.search(r'(Ping|Connect|Query|Exec)\s*\(.*ctx', line):
            # Functions that should check context cancellation
            if 'ctx.Err()' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="CTX_001",
                    message="Operation with context should check ctx.Err() for cancellation",
                    suggestion="Add 'if err := ctx.Err(); err != nil { return err }' before operation"
                ))
        
        # Check for goroutines without context handling
        if 'go func(' in line and 'ctx' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="CTX_002",
                message="Goroutine launched without context for cancellation",
                suggestion="Pass context to goroutine for proper cancellation handling"
            ))
        
        return issues
    
    def _check_context_timeout(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for context timeout patterns"""
        issues = []
        
        # Check for WithTimeout without defer cancel
        if 'context.WithTimeout' in line or 'context.WithDeadline' in line:
            # Look for assignment pattern
            if '=' in line and 'defer' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="CTX_003",
                    message="Context with timeout/deadline should have defer cancel()",
                    suggestion="Add 'defer cancel()' after context creation"
                ))
        
        # Check for very long or very short timeouts
        timeout_match = re.search(r'(\d+)\s*\*\s*time\.(Second|Minute|Hour)', line)
        if timeout_match:
            value = int(timeout_match.group(1))
            unit = timeout_match.group(2)
            
            if unit == 'Second' and value > 300:  # > 5 minutes
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="CTX_004",
                    message=f"Very long timeout ({value} seconds) may cause resource leaks",
                    suggestion="Consider if such a long timeout is necessary"
                ))
            elif unit == 'Second' and value < 1:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="CTX_005",
                    message=f"Very short timeout ({value} second) may cause frequent failures",
                    suggestion="Increase timeout or use context.WithCancel for manual control"
                ))
        
        return issues
    
    def _check_context_propagation(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for proper context propagation"""
        issues = []
        
        # Check for context.Background() in non-main functions
        if 'context.Background()' in line:
            # This should generally only be used in main() or top-level handlers
            if 'func main(' not in line and 'func Test' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="CTX_006",
                    message="context.Background() used in non-main function",
                    suggestion="Propagate context from caller instead of creating new background context"
                ))
        
        # Check for context.TODO() in production code
        if 'context.TODO()' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="CTX_007",
                message="context.TODO() should be replaced with proper context",
                suggestion="Use context from caller or create appropriate context with timeout/cancellation"
            ))
        
        return issues
    
    def _check_function_signatures(self, file_path: Path, content: str) -> List[LintIssue]:
        """Check function signatures for proper context usage"""
        issues = []
        
        # Find function definitions
        func_pattern = r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(([^)]*)\)\s*(?:\([^)]*\))?\s*(?:error\s*)?{'
        
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            func_name = match.group(1)
            params = match.group(2)
            line_num = content[:match.start()].count('\n') + 1
            
            # Skip certain function types
            if func_name in ['main', 'init'] or func_name.startswith('Test'):
                continue
            
            # Check if function should have context parameter
            has_context = 'ctx context.Context' in params or 'context.Context' in params
            
            # Functions that typically should have context
            should_have_context = any(keyword in func_name.lower() for keyword in [
                'get', 'list', 'create', 'update', 'delete', 'query', 'exec',
                'fetch', 'load', 'save', 'send', 'process'
            ])
            
            if should_have_context and not has_context:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="CTX_008",
                    message=f"Function '{func_name}' should accept context.Context parameter",
                    suggestion="Add 'ctx context.Context' as first parameter for cancellation support"
                ))
            
            # Check context parameter position (should be first)
            if has_context and not params.strip().startswith('ctx context.Context'):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="CTX_009",
                    message="Context parameter should be first in function signature",
                    suggestion="Move context.Context to be the first parameter"
                ))
        
        return issues