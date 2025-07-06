"""
React Linter - Catches common React issues that CodeRabbit flags

Focuses on performance, hooks rules, component patterns, and React best practices
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import NodeJSLinter, LintIssue, LintSeverity


class ReactLinter(NodeJSLinter):
    """Linter for React-specific issues"""
    
    def __init__(self):
        super().__init__("react", ["*.tsx", "*.jsx"])
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint a React file for common issues"""
        if not file_path.suffix in ['.tsx', '.jsx']:
            return []
            
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            # Only lint files that import React
            if not self._is_react_file(content):
                return []
                
            # Check for various React issues
            issues.extend(self._check_missing_dependency_arrays(file_path, lines))
            issues.extend(self._check_missing_memoization(file_path, lines))
            issues.extend(self._check_inline_objects_in_jsx(file_path, lines))
            issues.extend(self._check_missing_key_props(file_path, lines))
            issues.extend(self._check_unsafe_hooks_usage(file_path, lines))
            issues.extend(self._check_component_naming(file_path, lines))
            issues.extend(self._check_missing_error_boundaries(file_path, lines))
            issues.extend(self._check_accessibility_issues(file_path, lines))
            issues.extend(self._check_performance_anti_patterns(file_path, lines))
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
        return issues
    
    def _is_react_file(self, content: str) -> bool:
        """Check if file is a React component file"""
        react_indicators = [
            r'import.*React',
            r'from [\'"]react[\'"]',
            r'\.jsx?',
            r'\.tsx?',
            r'<\w+.*>',  # JSX tags
        ]
        
        return any(re.search(pattern, content) for pattern in react_indicators)
    
    def _check_missing_dependency_arrays(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for useEffect, useCallback, useMemo without proper dependency arrays"""
        issues = []
        
        hook_patterns = [
            (r'useEffect\s*\(\s*\(\s*\)\s*=>', 'useEffect'),
            (r'useCallback\s*\(\s*\(', 'useCallback'),
            (r'useMemo\s*\(\s*\(\s*\)\s*=>', 'useMemo'),
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern, hook_name in hook_patterns:
                if re.search(pattern, line):
                    # Check if dependency array is present
                    # Look for closing bracket and dependency array in next few lines
                    has_deps = False
                    for check_line_num in range(line_num, min(line_num + 5, len(lines))):
                        check_line = lines[check_line_num - 1]
                        if re.search(r'\],\s*\[.*\]\s*\)', check_line):
                            has_deps = True
                            break
                    
                    if not has_deps:
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.HIGH,
                            rule_id="react-missing-deps",
                            message=f"{hook_name} is missing dependency array",
                            suggestion=f"Add dependency array as second argument to {hook_name}"
                        ))
                        
        return issues
    
    def _check_missing_memoization(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for components that should be memoized"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for component definitions that might benefit from memoization
            component_patterns = [
                r'export\s+function\s+(\w+)\s*\(',
                r'const\s+(\w+)\s*=\s*\(',
            ]
            
            for pattern in component_patterns:
                match = re.search(pattern, line)
                if match:
                    component_name = match.group(1)
                    
                    # Check if component name starts with capital (React component)
                    if component_name[0].isupper():
                        # Look for React.memo or memo usage
                        has_memo = False
                        for check_line in lines:
                            if re.search(rf'React\.memo\s*\(\s*{component_name}', check_line) or \
                               re.search(rf'memo\s*\(\s*{component_name}', check_line):
                                has_memo = True
                                break
                        
                        if not has_memo:
                            # Check if component has props (might benefit from memoization)
                            if '(' in line and ')' in line:
                                issues.append(self._create_issue(
                                    file_path=file_path,
                                    line_number=line_num,
                                    severity=LintSeverity.MEDIUM,
                                    rule_id="react-missing-memo",
                                    message=f"Component '{component_name}' might benefit from React.memo()",
                                    suggestion="Consider wrapping component with React.memo() to prevent unnecessary re-renders"
                                ))
                        
        return issues
    
    def _check_inline_objects_in_jsx(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for inline objects/arrays in JSX that cause re-renders"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for inline objects in JSX
            inline_patterns = [
                r'style=\{\{',           # style={{}}
                r'=\{\[\s*\]',          # prop={[]}
                r'=\{\{\s*\w+:',        # prop={{key: value}}
            ]
            
            for pattern in inline_patterns:
                if re.search(pattern, line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="react-inline-object",
                        message="Inline objects/arrays in JSX cause unnecessary re-renders",
                        suggestion="Move object/array outside component or use useMemo()"
                    ))
                    
        return issues
    
    def _check_missing_key_props(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for missing key props in mapped elements"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for map functions that render JSX
            if re.search(r'\.map\s*\(\s*\(.*\)\s*=>\s*<', line):
                # Check if key prop is present
                if 'key=' not in line:
                    # Look ahead in next few lines for key prop
                    has_key = False
                    for check_line_num in range(line_num, min(line_num + 3, len(lines))):
                        if 'key=' in lines[check_line_num - 1]:
                            has_key = True
                            break
                    
                    if not has_key:
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.HIGH,
                            rule_id="react-missing-key",
                            message="Missing 'key' prop in mapped element",
                            suggestion="Add unique 'key' prop to mapped elements for proper React reconciliation"
                        ))
                        
        return issues
    
    def _check_unsafe_hooks_usage(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for hooks called conditionally or in loops"""
        issues = []
        
        hook_pattern = r'use[A-Z]\w*\s*\('
        
        for line_num, line in enumerate(lines, 1):
            if re.search(hook_pattern, line):
                # Check if hook is inside conditional or loop
                # Look at indentation and previous lines for if/for statements
                indent = len(line) - len(line.lstrip())
                
                for check_line_num in range(max(1, line_num - 5), line_num):
                    check_line = lines[check_line_num - 1]
                    check_indent = len(check_line) - len(check_line.lstrip())
                    
                    if check_indent < indent:
                        if re.search(r'\b(if|for|while|switch)\s*\(', check_line):
                            issues.append(self._create_issue(
                                file_path=file_path,
                                line_number=line_num,
                                severity=LintSeverity.HIGH,
                                rule_id="react-hooks-rules",
                                message="Hooks must not be called inside loops, conditions, or nested functions",
                                suggestion="Move hook call to top level of component function"
                            ))
                            break
                            
        return issues
    
    def _check_component_naming(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for proper component naming conventions"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for component definitions
            component_match = re.search(r'(?:export\s+)?(?:function|const)\s+(\w+)', line)
            if component_match:
                component_name = component_match.group(1)
                
                # Check if it's a React component (returns JSX)
                if self._returns_jsx(lines, line_num):
                    if not component_name[0].isupper():
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.MEDIUM,
                            rule_id="react-component-naming",
                            message=f"React component '{component_name}' should start with uppercase letter",
                            suggestion="Rename component to start with uppercase letter (PascalCase)"
                        ))
                        
        return issues
    
    def _check_missing_error_boundaries(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for components that should have error boundaries"""
        issues = []
        
        content = '\n'.join(lines)
        
        # Check if file has async operations but no error boundary
        has_async = any(pattern in content for pattern in [
            'useQuery', 'useMutation', 'fetch(', 'axios.', 'async ', 'await '
        ])
        
        has_error_boundary = any(pattern in content for pattern in [
            'ErrorBoundary', 'componentDidCatch', 'getDerivedStateFromError'
        ])
        
        if has_async and not has_error_boundary:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=1,
                severity=LintSeverity.MEDIUM,
                rule_id="react-missing-error-boundary",
                message="Component with async operations should be wrapped in ErrorBoundary",
                suggestion="Add ErrorBoundary wrapper or implement error handling"
            ))
            
        return issues
    
    def _check_accessibility_issues(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for basic accessibility issues"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for images without alt text
            if re.search(r'<img\s+', line) and 'alt=' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="react-missing-alt",
                    message="Image missing alt attribute for accessibility",
                    suggestion="Add alt attribute with descriptive text or empty string for decorative images"
                ))
            
            # Check for buttons without accessible text
            if re.search(r'<button[^>]*>\s*<', line):  # Button with only child elements
                if not re.search(r'aria-label=|title=', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="react-button-accessibility",
                        message="Button with only child elements needs aria-label for accessibility",
                        suggestion="Add aria-label attribute to describe button purpose"
                    ))
                    
        return issues
    
    def _check_performance_anti_patterns(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for React performance anti-patterns"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for creating functions in render
            if re.search(r'onClick=\{.*=>', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="react-inline-function",
                    message="Inline arrow functions in JSX props cause re-renders",
                    suggestion="Use useCallback or define function outside render"
                ))
            
            # Check for spreading props without memoization
            if re.search(r'\.\.\.\w+', line) and 'useMemo' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="react-spread-props",
                    message="Spreading props can cause unnecessary re-renders",
                    suggestion="Consider memoizing spread props or destructuring specific props"
                ))
                
        return issues
    
    def _returns_jsx(self, lines: List[str], start_line: int) -> bool:
        """Check if function returns JSX"""
        for line_num in range(start_line, min(start_line + 20, len(lines))):
            line = lines[line_num - 1]
            if re.search(r'return\s*<\w+', line) or re.search(r'return\s*\(.*<\w+', line):
                return True
        return False