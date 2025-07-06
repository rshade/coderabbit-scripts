"""
Go Code Duplication Linter
Catches duplicate comments, similar functions, and other code duplication issues
Based on CodeRabbit issues: Fix #6 (duplicate comments), Fix #33 (missing helper functions)
"""

import re
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict

from ..base_linter import GoLinter, LintIssue, LintSeverity


class DuplicationLinter(GoLinter):
    """Linter for code duplication issues in Go code"""
    
    def __init__(self):
        super().__init__("duplication")
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Check Go file for code duplication issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Check for duplicate comments
            issues.extend(self._check_duplicate_comments(file_path, lines))
            
            # Check for undefined helper functions
            issues.extend(self._check_undefined_helpers(file_path, lines))
            
            # Check for similar function patterns
            issues.extend(self._check_similar_functions(file_path, lines))
            
            # Check for magic numbers
            issues.extend(self._check_magic_numbers(file_path, lines))
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_duplicate_comments(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for duplicate comments that could be consolidated"""
        issues = []
        comment_counts = defaultdict(list)
        
        for line_num, line in enumerate(lines, 1):
            # Extract comment content (without line number prefixes like //nolint)
            comment_match = re.search(r'//\s*(.+)', line)
            if comment_match:
                comment_text = comment_match.group(1).strip()
                
                # Skip certain types of comments that are expected to be duplicated
                skip_patterns = [
                    r'^nolint:',
                    r'^TODO:',
                    r'^FIXME:',
                    r'^NOTE:',
                    r'^\d+',  # Line numbers
                    r'^$',    # Empty comments
                ]
                
                should_skip = any(re.match(pattern, comment_text) for pattern in skip_patterns)
                if not should_skip and len(comment_text) > 10:  # Only check substantial comments
                    comment_counts[comment_text].append(line_num)
        
        # Report duplicates
        for comment_text, line_numbers in comment_counts.items():
            if len(line_numbers) > 1:
                # Check if the comments are far apart (more than 5 lines)
                if max(line_numbers) - min(line_numbers) > 5:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_numbers[1],  # Report second occurrence
                        severity=LintSeverity.LOW,
                        rule_id="DUP_001",
                        message=f"Duplicate comment found: '{comment_text[:50]}...'",
                        suggestion="Consider consolidating duplicate comments or making them more specific"
                    ))
        
        return issues
    
    def _check_undefined_helpers(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for undefined helper functions that are referenced"""
        issues = []
        
        # Common helper function patterns that might be missing
        helper_calls = set()
        helper_definitions = set()
        
        for line_num, line in enumerate(lines, 1):
            # Look for function calls that might be helpers
            helper_patterns = [
                r'(\w+Ptr)\(',  # Pointer helper functions like StringPtr, IntPtr
                r'(String|Int|Float64|Bool)\(',  # Type conversion helpers
                r'(to\w+Ptr)\(',  # Conversion to pointer helpers
            ]
            
            for pattern in helper_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    helper_calls.add(match.group(1))
            
            # Look for function definitions
            func_match = re.search(r'func\s+(\w+)\(', line)
            if func_match:
                helper_definitions.add(func_match.group(1))
        
        # Report undefined helpers
        undefined_helpers = helper_calls - helper_definitions
        for helper in undefined_helpers:
            # Find the line where it's called
            for line_num, line in enumerate(lines, 1):
                if f'{helper}(' in line:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.HIGH,
                        rule_id="DUP_002",
                        message=f"Undefined helper function '{helper}' called",
                        suggestion=f"Define {helper} function or use existing helper with correct name"
                    ))
                    break
        
        return issues
    
    def _check_similar_functions(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for similar functions that could be consolidated"""
        issues = []
        functions = []
        
        current_function = None
        function_start = 0
        brace_count = 0
        
        for line_num, line in enumerate(lines, 1):
            # Start of function
            func_match = re.search(r'func\s+(\w+)\s*\(([^)]*)\)', line)
            if func_match and current_function is None:
                current_function = {
                    'name': func_match.group(1),
                    'params': func_match.group(2),
                    'start_line': line_num,
                    'lines': []
                }
                function_start = line_num
                
            if current_function:
                current_function['lines'].append(line.strip())
                
                # Count braces to find end of function
                brace_count += line.count('{') - line.count('}')
                
                if brace_count == 0 and '{' in line:
                    # End of function
                    functions.append(current_function)
                    current_function = None
        
        # Check for similar function patterns
        for i, func1 in enumerate(functions):
            for func2 in functions[i+1:]:
                similarity = self._calculate_function_similarity(func1, func2)
                if similarity > 0.8:  # 80% similar
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=func2['start_line'],
                        severity=LintSeverity.MEDIUM,
                        rule_id="DUP_003",
                        message=f"Function '{func2['name']}' is very similar to '{func1['name']}'",
                        suggestion="Consider extracting common logic into a shared helper function"
                    ))
        
        return issues
    
    def _check_magic_numbers(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for magic numbers that should be constants"""
        issues = []
        
        # Common magic numbers that should be constants
        magic_patterns = [
            (r'\b(50|100|200|255|500|1000|2000|5000|10000)\b', 'Consider defining as named constant'),
            (r'\b(24|60|3600|86400)\b', 'Time-related magic number - consider named constant'),
            (r'\b(8080|3000|8000|443|80)\b', 'Port number - consider configuration or constant'),
        ]
        
        for line_num, line in enumerate(lines, 1):
            # Skip certain contexts where magic numbers are acceptable
            if any(keyword in line.lower() for keyword in ['test', 'example', 'timeout', 'sleep']):
                continue
                
            for pattern, suggestion in magic_patterns:
                if re.search(pattern, line):
                    # Make sure it's not in a comment or string
                    if '//' not in line.split(pattern)[0] and '"' not in line:
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.LOW,
                            rule_id="DUP_004",
                            message=f"Magic number detected: {pattern}",
                            suggestion=suggestion
                        ))
        
        return issues
    
    def _calculate_function_similarity(self, func1: Dict, func2: Dict) -> float:
        """Calculate similarity between two functions (0.0 to 1.0)"""
        lines1 = [line for line in func1['lines'] if line and not line.startswith('//')]
        lines2 = [line for line in func2['lines'] if line and not line.startswith('//')]
        
        if not lines1 or not lines2:
            return 0.0
        
        # Simple similarity based on common lines
        common_lines = len(set(lines1) & set(lines2))
        total_lines = len(set(lines1) | set(lines2))
        
        return common_lines / total_lines if total_lines > 0 else 0.0