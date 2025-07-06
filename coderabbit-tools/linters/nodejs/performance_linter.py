"""
Node.js Performance Linter - Catches performance issues in JavaScript/TypeScript

Focuses on bundle size, memory leaks, inefficient patterns, and performance anti-patterns
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import NodeJSLinter, LintIssue, LintSeverity


class NodeJSPerformanceLinter(NodeJSLinter):
    """Linter for Node.js/JavaScript performance issues"""
    
    def __init__(self):
        super().__init__("nodejs_performance", ["*.js", "*.ts", "*.jsx", "*.tsx"])
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint a JavaScript/TypeScript file for performance issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            # Check for various performance issues
            issues.extend(self._check_large_bundle_imports(file_path, lines))
            issues.extend(self._check_memory_leaks(file_path, lines))
            issues.extend(self._check_inefficient_loops(file_path, lines))
            issues.extend(self._check_unnecessary_re_renders(file_path, lines))
            issues.extend(self._check_blocking_operations(file_path, lines))
            issues.extend(self._check_inefficient_dom_queries(file_path, lines))
            issues.extend(self._check_heavy_computations(file_path, lines))
            issues.extend(self._check_bundle_optimization(file_path, lines))
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
        return issues
    
    def _check_large_bundle_imports(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for imports that may significantly increase bundle size"""
        issues = []
        
        large_libraries = {
            'lodash': 'Use specific imports: import { debounce } from "lodash/debounce"',
            'moment': 'Consider using date-fns or day.js for smaller bundle size',
            'rxjs': 'Use specific imports: import { map } from "rxjs/operators"',
            'antd': 'Use specific imports: import { Button } from "antd/lib/button"',
            '@material-ui/core': 'Use specific imports to reduce bundle size',
            'chart.js': 'Consider using a lighter charting library for simple charts',
        }
        
        for line_num, line in enumerate(lines, 1):
            # Check for full library imports
            for library, suggestion in large_libraries.items():
                if re.search(rf'import.*from\s+[\'\"]{library}[\'\"]\s*$', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="performance-large-import",
                        message=f"Importing entire '{library}' library may increase bundle size",
                        suggestion=suggestion
                    ))
            
            # Check for unnecessary polyfills
            polyfill_pattern = r'import.*[\'\"](core-js|babel-polyfill)[\'\""]'
            if re.search(polyfill_pattern, line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="performance-unnecessary-polyfill",
                    message="Consider if polyfills are necessary for your target browsers",
                    suggestion="Use browserslist and @babel/preset-env for targeted polyfills"
                ))
                
        return issues
    
    def _check_memory_leaks(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for potential memory leaks"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for event listeners without cleanup
            if re.search(r'addEventListener\s*\(', line):
                # Look for corresponding removeEventListener in the same function/component
                has_cleanup = False
                
                # Look ahead for cleanup (basic heuristic)
                for check_line_num in range(line_num, min(line_num + 20, len(lines))):
                    check_line = lines[check_line_num - 1]
                    if 'removeEventListener' in check_line or 'cleanup' in check_line.lower():
                        has_cleanup = True
                        break
                
                if not has_cleanup:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="performance-memory-leak-listener",
                        message="Event listener may not be cleaned up",
                        suggestion="Add removeEventListener in cleanup function or useEffect cleanup"
                    ))
            
            # Check for timers without cleanup
            timer_patterns = ['setTimeout', 'setInterval']
            for pattern in timer_patterns:
                if pattern in line:
                    # Look for corresponding clear function
                    clear_pattern = pattern.replace('set', 'clear')
                    has_clear = False
                    
                    for check_line_num in range(line_num, min(line_num + 15, len(lines))):
                        if clear_pattern in lines[check_line_num - 1]:
                            has_clear = True
                            break
                    
                    if not has_clear:
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.MEDIUM,
                            rule_id="performance-memory-leak-timer",
                            message=f"{pattern} may not be cleaned up",
                            suggestion=f"Clear timer with {clear_pattern} in cleanup function"
                        ))
                        
        return issues
    
    def _check_inefficient_loops(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for inefficient loop patterns"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for nested loops with high complexity
            if re.search(r'for\s*\(.*for\s*\(', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="performance-nested-loops",
                    message="Nested loops can have O(n²) complexity",
                    suggestion="Consider using more efficient algorithms or data structures"
                ))
            
            # Check for DOM queries inside loops
            if re.search(r'for\s*\(.*document\.', line) or re.search(r'forEach.*document\.', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="performance-dom-in-loop",
                    message="DOM queries inside loops are expensive",
                    suggestion="Cache DOM elements outside the loop"
                ))
            
            # Check for expensive operations in loops
            expensive_ops = ['JSON.parse', 'JSON.stringify', 'localStorage', 'sessionStorage']
            for op in expensive_ops:
                if re.search(rf'(for|forEach).*{op}', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="performance-expensive-in-loop",
                        message=f"Expensive operation '{op}' inside loop",
                        suggestion="Move expensive operations outside loop when possible"
                    ))
                    
        return issues
    
    def _check_unnecessary_re_renders(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for patterns that cause unnecessary re-renders in React"""
        issues = []
        
        # Only check React files
        content = '\n'.join(lines)
        if not any(indicator in content for indicator in ['import React', 'from "react"', 'from \'react\'']):
            return issues
        
        for line_num, line in enumerate(lines, 1):
            # Check for object creation in render
            if re.search(r'=\s*\{[^}]*\}', line) and not re.search(r'useMemo|useCallback', line):
                # Skip variable declarations
                if not re.search(r'(const|let|var)\s+\w+\s*=', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="performance-object-in-render",
                        message="Object creation in render can cause unnecessary re-renders",
                        suggestion="Move object outside component or use useMemo()"
                    ))
            
            # Check for array creation in render
            if re.search(r'=\s*\[[^\]]*\]', line) and not re.search(r'useMemo|useState', line):
                if not re.search(r'(const|let|var)\s+\w+\s*=', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="performance-array-in-render",
                        message="Array creation in render can cause unnecessary re-renders",
                        suggestion="Move array outside component or use useMemo()"
                    ))
                    
        return issues
    
    def _check_blocking_operations(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for operations that block the main thread"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for synchronous operations that should be async
            blocking_patterns = [
                (r'fs\.readFileSync', 'Use fs.readFile or fs.promises.readFile'),
                (r'fs\.writeFileSync', 'Use fs.writeFile or fs.promises.writeFile'),
                (r'child_process\.execSync', 'Use child_process.exec or spawn'),
                (r'XMLHttpRequest', 'Use fetch() or axios for better async handling'),
            ]
            
            for pattern, suggestion in blocking_patterns:
                if re.search(pattern, line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="performance-blocking-operation",
                        message="Synchronous operation may block the main thread",
                        suggestion=suggestion
                    ))
            
            # Check for heavy computations without workers
            if re.search(r'(for|while).*\{.*Math\.(pow|sqrt|sin|cos)', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="performance-heavy-computation",
                    message="Heavy computation may block UI thread",
                    suggestion="Consider using Web Workers for CPU-intensive tasks"
                ))
                
        return issues
    
    def _check_inefficient_dom_queries(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for inefficient DOM queries"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for repeated DOM queries
            query_methods = ['getElementById', 'getElementsByClassName', 'querySelector', 'querySelectorAll']
            
            for method in query_methods:
                if method in line:
                    # Look for same query in nearby lines
                    current_query = re.search(rf'{method}\s*\([^)]+\)', line)
                    if current_query:
                        query_text = current_query.group()
                        
                        # Check next 5 lines for same query
                        for check_line_num in range(line_num + 1, min(line_num + 6, len(lines))):
                            if query_text in lines[check_line_num - 1]:
                                issues.append(self._create_issue(
                                    file_path=file_path,
                                    line_number=line_num,
                                    severity=LintSeverity.MEDIUM,
                                    rule_id="performance-repeated-dom-query",
                                    message="Repeated DOM query detected",
                                    suggestion="Cache DOM element in a variable"
                                ))
                                break
            
            # Check for queries in loops (already covered but more specific)
            if re.search(r'querySelector.*forEach|querySelectorAll.*for', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="performance-dom-query-in-loop",
                    message="DOM queries inside loops are very expensive",
                    suggestion="Cache queries outside loop or use event delegation"
                ))
                
        return issues
    
    def _check_heavy_computations(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for heavy computations that should be optimized"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for complex regular expressions
            if 'new RegExp' in line or '/.*/' in line:
                # Check for complex patterns
                complex_patterns = [r'\.\*\+', r'\.\+\*', r'\(\?\!', r'\(\?\<']
                if any(pattern in line for pattern in complex_patterns):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.LOW,
                        rule_id="performance-complex-regex",
                        message="Complex regular expression may be slow",
                        suggestion="Test regex performance and consider simpler alternatives"
                    ))
            
            # Check for large array operations
            if re.search(r'\.(sort|filter|map|reduce)\s*\(', line):
                # If chained, it's less efficient
                if line.count('.') > 3:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.LOW,
                        rule_id="performance-chained-array-ops",
                        message="Long chains of array operations can be inefficient",
                        suggestion="Consider combining operations or using for loops for large datasets"
                    ))
                    
        return issues
    
    def _check_bundle_optimization(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for bundle optimization opportunities"""
        issues = []
        
        # Check package.json for optimization opportunities
        if file_path.name == 'package.json':
            content = '\n'.join(lines)
            
            # Check for dev dependencies in production
            if '"dependencies"' in content and '"devDependencies"' in content:
                # This is a complex check that would need JSON parsing
                # For now, just flag if both sections exist
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.LOW,
                    rule_id="performance-bundle-deps",
                    message="Review dependencies vs devDependencies for optimal bundle size",
                    suggestion="Ensure build tools are in devDependencies, not dependencies"
                ))
        
        # Check for missing lazy loading
        for line_num, line in enumerate(lines, 1):
            if re.search(r'import.*from\s+[\'\"]\./.*[\'\""]', line):
                # Check if it's a component import that could be lazy loaded
                if re.search(r'(Page|Screen|View|Component)', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.LOW,
                        rule_id="performance-missing-lazy-load",
                        message="Large component could benefit from lazy loading",
                        suggestion="Consider using React.lazy() for route-level components"
                    ))
                    
        return issues