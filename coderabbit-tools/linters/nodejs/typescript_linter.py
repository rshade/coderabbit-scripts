"""
TypeScript Linter - Catches common TypeScript issues that CodeRabbit flags

Focuses on type safety, proper TypeScript patterns, and avoiding common pitfalls
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import NodeJSLinter, LintIssue, LintSeverity


class TypeScriptLinter(NodeJSLinter):
    """Linter for TypeScript-specific issues"""
    
    def __init__(self):
        super().__init__("typescript", ["*.ts", "*.tsx"])
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint a TypeScript file for common issues"""
        if not file_path.suffix in ['.ts', '.tsx']:
            return []
            
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            # Check for various TypeScript issues
            issues.extend(self._check_any_type_usage(file_path, lines))
            issues.extend(self._check_unknown_without_type_guards(file_path, lines))
            issues.extend(self._check_missing_return_types(file_path, lines))
            issues.extend(self._check_unsafe_type_assertions(file_path, lines))
            issues.extend(self._check_non_null_assertions(file_path, lines))
            issues.extend(self._check_implicit_any_returns(file_path, lines))
            issues.extend(self._check_ts_ignore_comments(file_path, lines))
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
        return issues
    
    def _check_any_type_usage(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for usage of 'any' type without justification"""
        issues = []
        
        # Pattern to match 'any' type usage
        any_patterns = [
            r':\s*any\b',           # : any
            r'<any>',               # <any>
            r'as\s+any\b',          # as any
            r'Array<any>',          # Array<any>
            r'Record<.*?,\s*any>',  # Record<string, any>
        ]
        
        for line_num, line in enumerate(lines, 1):
            # Skip if line has justification comment
            if '// any is justified' in line or '/* any:' in line:
                continue
                
            for pattern in any_patterns:
                if re.search(pattern, line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.HIGH,
                        rule_id="ts-no-any",
                        message="Avoid using 'any' type - use specific types or 'unknown' with type guards",
                        suggestion="Replace 'any' with specific type or 'unknown' with proper type guards"
                    ))
                    
        return issues
    
    def _check_unknown_without_type_guards(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for 'unknown' type usage without proper type guards"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check if line uses unknown type
            if re.search(r':\s*unknown\b', line):
                # Look ahead for type guards within next 10 lines
                has_type_guard = False
                for check_line_num in range(line_num, min(line_num + 10, len(lines))):
                    check_line = lines[check_line_num - 1]
                    type_guard_patterns = [
                        r'typeof\s+\w+\s*===',
                        r'Array\.isArray\(',
                        r'\w+\s+instanceof\s+',
                        r'if\s*\(.*\)',
                    ]
                    
                    if any(re.search(pattern, check_line) for pattern in type_guard_patterns):
                        has_type_guard = True
                        break
                
                if not has_type_guard:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="ts-unknown-type-guard",
                        message="'unknown' type should be used with type guards for safe access",
                        suggestion="Add type guards (typeof, Array.isArray, instanceof) before using unknown values"
                    ))
                    
        return issues
    
    def _check_missing_return_types(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for functions missing explicit return types"""
        issues = []
        
        function_patterns = [
            r'^\s*export\s+function\s+\w+\s*\([^)]*\)\s*{',  # export function
            r'^\s*function\s+\w+\s*\([^)]*\)\s*{',          # function
            r'^\s*const\s+\w+\s*=\s*\([^)]*\)\s*=>\s*{',    # arrow function
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern in function_patterns:
                if re.search(pattern, line):
                    # Check if return type is specified
                    if not re.search(r'\):\s*\w+', line):
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.MEDIUM,
                            rule_id="ts-explicit-return-type",
                            message="Functions should have explicit return types",
                            suggestion="Add explicit return type annotation: ': ReturnType'"
                        ))
                        
        return issues
    
    def _check_unsafe_type_assertions(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for potentially unsafe type assertions"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for 'as' assertions
            as_matches = re.findall(r'as\s+(\w+)', line)
            for type_name in as_matches:
                if type_name in ['string', 'number', 'boolean', 'object']:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="ts-unsafe-assertion",
                        message=f"Type assertion 'as {type_name}' may be unsafe",
                        suggestion="Consider using type guards or proper type checking instead of assertions"
                    ))
                    
        return issues
    
    def _check_non_null_assertions(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for excessive use of non-null assertion operator (!)"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Count non-null assertions in line
            non_null_count = len(re.findall(r'!\s*[.\[]', line))
            
            if non_null_count > 2:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="ts-excessive-non-null",
                    message="Excessive use of non-null assertion operator (!)",
                    suggestion="Consider proper null checking instead of multiple non-null assertions"
                ))
                
        return issues
    
    def _check_implicit_any_returns(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for functions that implicitly return 'any'"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Functions that might return implicit any
            if re.search(r'JSON\.parse\(', line) and not re.search(r'as\s+\w+', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="ts-implicit-any-json",
                    message="JSON.parse returns 'any' - add type assertion or validation",
                    suggestion="Use JSON.parse(...) as YourType or add runtime validation"
                ))
                
        return issues
    
    def _check_ts_ignore_comments(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for @ts-ignore comments that should be replaced with proper types"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            if '@ts-ignore' in line and 'TODO:' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="ts-ignore-comment",
                    message="@ts-ignore should be avoided - fix the underlying type issue",
                    suggestion="Replace @ts-ignore with proper types or add TODO comment explaining why it's needed"
                ))
                
        return issues