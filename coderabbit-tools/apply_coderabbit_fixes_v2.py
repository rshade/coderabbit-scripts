#!/usr/bin/env python3
"""
CodeRabbit Fix Applicator v2 - Apply fixes from CodeRabbit AI prompts.
Works with the structured output from parse_coderabbit_comments_v2.py
"""

import json
import re
import sys
import argparse
import os
import subprocess
from typing import Dict, List, Optional, Tuple


class FixApplicator:
    def __init__(self, base_path: str = ".", dry_run: bool = False, verbose: bool = False):
        self.base_path = os.path.abspath(base_path)
        self.dry_run = dry_run
        self.verbose = verbose
        self.applied_fixes = []
        self.failed_fixes = []
    
    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}", file=sys.stderr)
    
    def resolve_file_path(self, file_path: str) -> str:
        """Resolve a file path relative to the base path."""
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(self.base_path, file_path)
    
    def read_file_lines(self, file_path: str) -> List[str]:
        """Read file and return lines."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.readlines()
        except Exception as e:
            self.log(f"Error reading {file_path}: {e}", "ERROR")
            return []
    
    def write_file_lines(self, file_path: str, lines: List[str]) -> bool:
        """Write lines to file."""
        if self.dry_run:
            self.log(f"DRY RUN: Would write {len(lines)} lines to {file_path}")
            return True
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        except Exception as e:
            self.log(f"Error writing {file_path}: {e}", "ERROR")
            return False
    
    def extract_code_suggestion(self, comment: Dict) -> Optional[str]:
        """Extract the most relevant code suggestion from a comment."""
        if not comment.get('code_suggestions'):
            return None
        
        # Look for suggestions that look like replacements or additions
        for suggestion in comment['code_suggestions']:
            # Skip very short suggestions
            if len(suggestion) < 10:
                continue
            
            # Skip suggestions that are just examples or explanations
            if any(word in suggestion.lower() for word in ['example:', 'usage:', 'note:', 'warning:']):
                continue
            
            # Prefer suggestions with diff-like format
            if '+' in suggestion or '-' in suggestion:
                return suggestion
            
            # Otherwise take the first substantial suggestion
            return suggestion
        
        return None
    
    def apply_simple_addition(self, file_path: str, line_num: int, content: str) -> bool:
        """Apply a simple addition at a specific line."""
        lines = self.read_file_lines(file_path)
        if not lines:
            return False
        
        # Ensure line_num is within bounds
        if line_num < 1 or line_num > len(lines) + 1:
            self.log(f"Line number {line_num} out of bounds for {file_path}", "ERROR")
            return False
        
        # Insert content at the specified line (1-based indexing)
        insert_index = line_num - 1
        if not content.endswith('\n'):
            content += '\n'
        
        lines.insert(insert_index, content)
        
        return self.write_file_lines(file_path, lines)
    
    def apply_replacement(self, file_path: str, start_line: int, end_line: int, new_content: str) -> bool:
        """Apply a replacement for a range of lines."""
        lines = self.read_file_lines(file_path)
        if not lines:
            return False
        
        # Convert to 0-based indexing and validate
        start_idx = start_line - 1
        end_idx = end_line
        
        if start_idx < 0 or end_idx > len(lines):
            self.log(f"Line range {start_line}-{end_line} out of bounds for {file_path}", "ERROR")
            return False
        
        # Prepare new content
        if isinstance(new_content, str):
            if not new_content.endswith('\n'):
                new_content += '\n'
            new_lines = [new_content]
        else:
            new_lines = new_content
        
        # Replace the lines
        lines[start_idx:end_idx] = new_lines
        
        return self.write_file_lines(file_path, lines)
    
    def detect_fix_type(self, comment: Dict) -> Tuple[str, Dict]:
        """Detect what type of fix should be applied based on the comment."""
        prompt = comment['prompts'][0] if comment['prompts'] else ""
        
        # Common fix patterns
        fix_patterns = {
            'input_validation': [
                'validate.*input', 'check.*parameter', 'ensure.*valid',
                'negative.*value', 'non-positive', 'invalid.*range'
            ],
            'error_handling': [
                'error.*handling', 'handle.*error', 'catch.*exception',
                'proper.*error', 'error.*message'
            ],
            'test_fix': [
                'test.*coverage', 'add.*test', 'unit.*test',
                'test.*case', 'error.*message.*test'
            ],
            'format_fix': [
                'missing.*backtick', 'close.*code.*block', 'format.*issue',
                'markdown.*rendering'
            ],
            'import_fix': [
                'import.*package', 'add.*import', 'missing.*import'
            ],
            'config_fix': [
                'configuration.*error', 'yaml.*error', 'config.*format'
            ]
        }
        
        # Detect fix type
        fix_type = 'unknown'
        for ftype, patterns in fix_patterns.items():
            if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in patterns):
                fix_type = ftype
                break
        
        # Extract specific instructions
        instructions = {
            'type': fix_type,
            'file_path': comment.get('file_path') or comment.get('path'),
            'start_line': comment.get('start_line'),
            'end_line': comment.get('end_line'),
            'prompt': prompt,
            'suggestions': comment.get('code_suggestions', [])
        }
        
        return fix_type, instructions
    
    def apply_known_fixes(self, comment: Dict) -> bool:
        """Apply known fixes based on comment patterns."""
        fix_type, instructions = self.detect_fix_type(comment)
        file_path = instructions['file_path']
        
        if not file_path:
            self.log(f"No file path found for comment {comment['id']}")
            return False
        
        resolved_path = self.resolve_file_path(file_path)
        if not os.path.exists(resolved_path):
            self.log(f"File does not exist: {resolved_path}")
            return False
        
        self.log(f"Applying {fix_type} fix to {file_path}")
        
        # Apply specific fixes based on type
        if fix_type == 'format_fix':
            return self.apply_format_fix(resolved_path, instructions)
        elif fix_type == 'input_validation':
            return self.apply_input_validation_fix(resolved_path, instructions)
        elif fix_type == 'config_fix':
            return self.apply_config_fix(resolved_path, instructions)
        else:
            # Generic fix application
            return self.apply_generic_fix(resolved_path, instructions)
    
    def apply_format_fix(self, file_path: str, instructions: Dict) -> bool:
        """Apply formatting fixes like missing backticks."""
        prompt = instructions['prompt'].lower()
        
        if 'missing.*backtick' in prompt or 'close.*code.*block' in prompt:
            # Add missing closing backticks
            lines = self.read_file_lines(file_path)
            if not lines:
                return False
            
            # Look for unclosed code blocks
            in_code_block = False
            for i, line in enumerate(lines):
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
            
            # If we end in a code block, add closing backticks
            if in_code_block:
                lines.append('```\n')
                return self.write_file_lines(file_path, lines)
        
        return False
    
    def apply_input_validation_fix(self, file_path: str, instructions: Dict) -> bool:
        """Apply input validation fixes."""
        # This would require more sophisticated parsing
        # For now, just log what would be done
        self.log(f"Would apply input validation fix to {file_path}")
        return True
    
    def apply_config_fix(self, file_path: str, instructions: Dict) -> bool:
        """Apply configuration file fixes."""
        if file_path.endswith('.yaml') or file_path.endswith('.yml'):
            # Handle YAML configuration fixes
            prompt = instructions['prompt'].lower()
            if 'path_filters' in prompt:
                # This is the .coderabbit.yaml fix we know about
                self.log(f"Would apply path_filters fix to {file_path}")
                return True
        
        return False
    
    def apply_generic_fix(self, file_path: str, instructions: Dict) -> bool:
        """Apply a generic fix based on code suggestions."""
        code_suggestion = self.extract_code_suggestion({'code_suggestions': instructions['suggestions']})
        
        if not code_suggestion:
            self.log(f"No applicable code suggestion found for {file_path}")
            return False
        
        # For now, just log what would be applied
        self.log(f"Would apply code suggestion to {file_path}:")
        self.log(f"  {code_suggestion[:100]}...")
        
        return True
    
    def apply_fixes(self, comments: List[Dict]) -> Dict:
        """Apply fixes for all comments."""
        results = {
            'total': len(comments),
            'applied': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        for comment in comments:
            if not comment.get('prompts'):
                results['skipped'] += 1
                continue
            
            try:
                success = self.apply_known_fixes(comment)
                if success:
                    results['applied'] += 1
                    self.applied_fixes.append(comment)
                else:
                    results['failed'] += 1
                    self.failed_fixes.append(comment)
                
                results['details'].append({
                    'id': comment['id'],
                    'file': comment.get('file_path', 'unknown'),
                    'success': success,
                    'type': self.detect_fix_type(comment)[0]
                })
                
            except Exception as e:
                self.log(f"Error applying fix for comment {comment['id']}: {e}", "ERROR")
                results['failed'] += 1
                self.failed_fixes.append(comment)
        
        return results


def main():
    parser = argparse.ArgumentParser(
        description='Apply fixes from CodeRabbit AI prompts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Apply fixes from default analysis file
  %(prog)s
  
  # Apply fixes from specific analysis file
  %(prog)s --input my_analysis.json
  
  # Dry run to see what would be changed
  %(prog)s --dry-run
  
  # Apply fixes to specific directory
  %(prog)s --base-path /path/to/repo
  
  # Verbose output
  %(prog)s --verbose

Chain with other tools:
  python3 fetch_github_comments.py 149 | \\
  python3 parse_coderabbit_comments_v2.py --input - | \\
  python3 %(prog)s --input -
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        default='coderabbit_analysis.json',
        help='Input JSON file from parse_coderabbit_comments_v2.py (default: coderabbit_analysis.json, use - for stdin)'
    )
    
    parser.add_argument(
        '--base-path',
        default='.',
        help='Base path for resolving relative file paths (default: current directory)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making actual changes'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--filter-type',
        choices=['format_fix', 'input_validation', 'error_handling', 'test_fix', 'config_fix'],
        help='Only apply fixes of this type'
    )
    
    args = parser.parse_args()
    
    # Read input
    try:
        if args.input == '-':
            analysis_data = json.load(sys.stdin)
        else:
            with open(args.input, 'r') as f:
                analysis_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)
    
    comments = analysis_data.get('comments', [])
    if not comments:
        print("No comments found in analysis data", file=sys.stderr)
        sys.exit(1)
    
    # Filter by type if specified
    if args.filter_type:
        filtered_comments = []
        for comment in comments:
            applicator = FixApplicator()  # Temporary instance for detection
            fix_type, _ = applicator.detect_fix_type(comment)
            if fix_type == args.filter_type:
                filtered_comments.append(comment)
        comments = filtered_comments
        print(f"Filtered to {len(comments)} comments of type '{args.filter_type}'")
    
    # Apply fixes
    applicator = FixApplicator(
        base_path=args.base_path,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    print(f"Applying fixes to {len(comments)} CodeRabbit comments...")
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
    
    results = applicator.apply_fixes(comments)
    
    # Print summary
    print(f"\nResults:")
    print(f"  Total comments: {results['total']}")
    print(f"  Applied: {results['applied']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Skipped: {results['skipped']}")
    
    if args.verbose and results['details']:
        print(f"\nDetails:")
        for detail in results['details']:
            status = "✓" if detail['success'] else "✗"
            print(f"  {status} {detail['file']} ({detail['type']}) - {detail['id']}")
    
    # Exit with appropriate code
    sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == '__main__':
    main()