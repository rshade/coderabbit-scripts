#!/usr/bin/env python3
"""
CodeRabbit Comment Parser v2 - Parse CodeRabbit comments and extract AI prompts.
Works with the structured output from fetch_github_comments.py
"""

import json
import re
import sys
import argparse
from typing import Dict, List, Optional


def extract_ai_prompts(comment_body: str) -> List[str]:
    """Extract AI agent prompts from CodeRabbit comment body."""
    prompts = []
    
    # Look for "Prompt for AI Agents" section
    prompt_patterns = [
        r'<details>\s*<summary>🤖 Prompt for AI Agents</summary>\s*(.*?)</details>',
        r'<summary>🤖 Prompt for AI Agents</summary>\s*(.*?)</details>',
        r'## 🤖 Prompt for AI Agents\s*(.*?)(?=\n##|\n</details>|$)',
    ]
    
    for pattern in prompt_patterns:
        matches = re.findall(pattern, comment_body, re.DOTALL | re.IGNORECASE)
        for match in matches:
            # Clean up the prompt text
            prompt = match.strip()
            # Remove HTML tags
            prompt = re.sub(r'<[^>]+>', '', prompt)
            # Remove code fences if they're wrapping the whole prompt
            prompt = re.sub(r'^```\s*\n?(.*?)\n?```$', r'\1', prompt, flags=re.DOTALL)
            # Remove excessive whitespace
            prompt = ' '.join(prompt.split())
            if prompt and len(prompt) > 10:  # Filter out very short prompts
                prompts.append(prompt)
    
    return prompts


def extract_code_suggestions(comment_body: str) -> List[str]:
    """Extract code suggestions from comment body."""
    code_suggestions = []
    
    # Look for code blocks
    code_pattern = r'```[a-zA-Z]*\s*(.*?)```'
    code_matches = re.findall(code_pattern, comment_body, re.DOTALL)
    
    for code in code_matches:
        code = code.strip()
        if code and len(code) > 5:  # Filter out very short code blocks
            code_suggestions.append(code)
    
    return code_suggestions


def extract_file_path_from_prompt(prompt: str) -> Optional[str]:
    """Extract file path from AI prompt text."""
    patterns = [
        r'In\s+([^\s]+\.[a-zA-Z]+)\s+(?:around|between|at)',
        r'In\s+the\s+([^\s]+\.[a-zA-Z]+)\s+file',
        r'file\s+([^\s]+\.[a-zA-Z]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prompt)
        if match:
            return match.group(1)
    
    return None


def extract_line_info_from_prompt(prompt: str) -> tuple:
    """Extract line number information from prompt."""
    patterns = [
        r'around\s+lines?\s+(\d+)\s+(?:to|and)\s+(\d+)',
        r'between\s+lines?\s+(\d+)\s+(?:to|and)\s+(\d+)',
        r'around\s+line\s+(\d+)',
        r'at\s+line\s+(\d+)',
        r'lines?\s+(\d+)-(\d+)',
        r'lines?\s+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prompt)
        if match:
            if len(match.groups()) == 2:
                return int(match.group(1)), int(match.group(2))
            else:
                line = int(match.group(1))
                return line, line
    
    return None, None


def is_coderabbit_comment(comment: Dict) -> bool:
    """Check if a comment is from CodeRabbit."""
    if not isinstance(comment, dict):
        return False
    
    user = comment.get('user', {})
    if not isinstance(user, dict):
        return False
    
    login = user.get('login', '')
    return login.startswith('coderabbitai')


def parse_comment(comment: Dict, comment_type: str) -> Optional[Dict]:
    """Parse a single comment and extract relevant information."""
    if not is_coderabbit_comment(comment):
        return None
    
    body = comment.get('body', '')
    if not body:
        return None
    
    prompts = extract_ai_prompts(body)
    code_suggestions = extract_code_suggestions(body)
    
    # Only process comments that have prompts or substantial code suggestions
    if not prompts and len(code_suggestions) < 2:
        return None
    
    # Extract file and line info from first prompt if available
    file_path = None
    start_line = None
    end_line = None
    
    if prompts:
        file_path = extract_file_path_from_prompt(prompts[0])
        start_line, end_line = extract_line_info_from_prompt(prompts[0])
    
    return {
        'id': comment.get('id'),
        'type': comment_type,
        'url': comment.get('html_url', ''),
        'created_at': comment.get('created_at', ''),
        'updated_at': comment.get('updated_at', ''),
        'user': comment.get('user', {}).get('login', ''),
        'file_path': file_path,
        'start_line': start_line,
        'end_line': end_line,
        'body_preview': body[:300] + '...' if len(body) > 300 else body,
        'prompts': prompts,
        'code_suggestions': code_suggestions,
        'full_body': body
    }


def parse_github_comments(comments_data: Dict) -> List[Dict]:
    """Parse all CodeRabbit comments from GitHub comments data."""
    parsed_comments = []
    
    # Parse issue comments
    for comment in comments_data.get('issue_comments', []):
        parsed = parse_comment(comment, 'issue_comment')
        if parsed:
            parsed_comments.append(parsed)
    
    # Parse review comments (inline comments)
    for comment in comments_data.get('review_comments', []):
        parsed = parse_comment(comment, 'review_comment')
        if parsed:
            # Review comments have additional context
            parsed['path'] = comment.get('path', '')
            parsed['diff_hunk'] = comment.get('diff_hunk', '')
            parsed_comments.append(parsed)
    
    # Parse reviews
    for review in comments_data.get('reviews', []):
        parsed = parse_comment(review, 'review')
        if parsed:
            parsed['state'] = review.get('state', '')
            parsed_comments.append(parsed)
    
    return parsed_comments


def group_by_file(comments: List[Dict]) -> Dict[str, List[Dict]]:
    """Group comments by file path."""
    by_file = {}
    no_file = []
    
    for comment in comments:
        file_path = comment.get('file_path') or comment.get('path')
        if file_path:
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(comment)
        else:
            no_file.append(comment)
    
    if no_file:
        by_file['_no_file_specified'] = no_file
    
    return by_file


def print_summary(comments: List[Dict], repo: str, pr_number: int) -> None:
    """Print a summary of parsed comments."""
    print(f"\nCodeRabbit Analysis Summary for {repo} PR #{pr_number}")
    print("=" * 60)
    
    if not comments:
        print("No CodeRabbit comments with AI prompts found.")
        return
    
    print(f"Found {len(comments)} CodeRabbit comments with AI prompts/suggestions")
    
    # Group by type
    by_type = {}
    for comment in comments:
        comment_type = comment['type']
        if comment_type not in by_type:
            by_type[comment_type] = []
        by_type[comment_type].append(comment)
    
    print(f"\nBy comment type:")
    for comment_type, type_comments in by_type.items():
        print(f"  {comment_type}: {len(type_comments)}")
    
    # Group by file
    by_file = group_by_file(comments)
    print(f"\nBy file ({len(by_file)} files):")
    for file_path, file_comments in sorted(by_file.items()):
        print(f"  {file_path}: {len(file_comments)} comments")
    
    # Show prompts count
    total_prompts = sum(len(c['prompts']) for c in comments)
    total_code_suggestions = sum(len(c['code_suggestions']) for c in comments)
    print(f"\nContent:")
    print(f"  Total AI prompts: {total_prompts}")
    print(f"  Total code suggestions: {total_code_suggestions}")


def main():
    parser = argparse.ArgumentParser(
        description='Parse CodeRabbit comments and extract AI prompts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse from default input file
  %(prog)s
  
  # Parse from specific file
  %(prog)s --input my_comments.json
  
  # Parse and save to custom output
  %(prog)s --output coderabbit_analysis.json
  
  # Just show summary without saving
  %(prog)s --summary-only
  
Chain with fetcher:
  python3 fetch_github_comments.py 149 | python3 %(prog)s --input -
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        default='github_comments.json',
        help='Input JSON file from fetch_github_comments.py (default: github_comments.json, use - for stdin)'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='coderabbit_analysis.json',
        help='Output file for parsed CodeRabbit data (default: coderabbit_analysis.json)'
    )
    
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Only show summary, do not save parsed data'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'summary'],
        default='json',
        help='Output format (default: json)'
    )
    
    args = parser.parse_args()
    
    # Read input
    try:
        if args.input == '-':
            comments_data = json.load(sys.stdin)
        else:
            with open(args.input, 'r') as f:
                comments_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Parse comments
    parsed_comments = parse_github_comments(comments_data)
    
    # Get repo info for summary
    repo = comments_data.get('repo', 'unknown')
    pr_number = comments_data.get('pr_number', 0)
    
    # Show summary
    print_summary(parsed_comments, repo, pr_number)
    
    if not args.summary_only and parsed_comments:
        # Prepare output data
        output_data = {
            'repo': repo,
            'pr_number': pr_number,
            'parsed_at': comments_data.get('fetched_at'),
            'total_comments': len(parsed_comments),
            'comments': parsed_comments,
            'by_file': group_by_file(parsed_comments)
        }
        
        if args.format == 'json':
            # Save parsed data
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\nParsed data saved to: {args.output}")
        else:
            # Just output summary (already printed above)
            pass
    
    # Exit with appropriate code
    sys.exit(0 if parsed_comments else 1)


if __name__ == '__main__':
    main()