#!/usr/bin/env python3
"""
GitHub Comment Fetcher - Fetch all comments from a GitHub PR using gh CLI.
This utility can be used across multiple repositories and chained with other tools.
"""

import json
import subprocess
import sys
import argparse
import os
from typing import Dict, List, Optional


def run_gh_command(cmd: List[str]) -> Dict:
    """Run a gh CLI command and return the JSON response."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout) if result.stdout.strip() else []
    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e}", file=sys.stderr)
        print(f"stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_pr_comments(repo: str, pr_number: int) -> Dict:
    """Fetch all types of comments from a GitHub PR."""
    print(f"Fetching comments from {repo} PR #{pr_number}...", file=sys.stderr)
    
    comments_data = {
        'repo': repo,
        'pr_number': pr_number,
        'pr_comments': [],
        'issue_comments': [],
        'review_comments': [],
        'reviews': []
    }
    
    # Fetch PR/issue comments (general comments on the PR)
    print("Fetching issue comments...", file=sys.stderr)
    issue_comments = run_gh_command([
        'gh', 'api', f'/repos/{repo}/issues/{pr_number}/comments',
        '--paginate'
    ])
    comments_data['issue_comments'] = issue_comments
    
    # Fetch review comments (inline code comments)
    print("Fetching review comments...", file=sys.stderr)
    review_comments = run_gh_command([
        'gh', 'api', f'/repos/{repo}/pulls/{pr_number}/comments',
        '--paginate'
    ])
    comments_data['review_comments'] = review_comments
    
    # Fetch reviews (overall PR reviews)
    print("Fetching reviews...", file=sys.stderr)
    reviews = run_gh_command([
        'gh', 'api', f'/repos/{repo}/pulls/{pr_number}/reviews',
        '--paginate'
    ])
    comments_data['reviews'] = reviews
    
    # Fetch PR details for context
    print("Fetching PR details...", file=sys.stderr)
    pr_details = run_gh_command([
        'gh', 'api', f'/repos/{repo}/pulls/{pr_number}'
    ])
    comments_data['pr_details'] = pr_details
    
    return comments_data


def get_repo_from_remote() -> Optional[str]:
    """Get the repository name from git remote origin."""
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()
        
        # Parse different URL formats
        if url.startswith('https://github.com/'):
            repo = url.replace('https://github.com/', '')
        elif url.startswith('git@github.com:'):
            repo = url.replace('git@github.com:', '')
        else:
            return None
            
        # Remove .git suffix if present
        if repo.endswith('.git'):
            repo = repo[:-4]
            
        return repo
    except subprocess.CalledProcessError:
        return None


def save_comments(comments_data: Dict, output_file: str) -> None:
    """Save comments data to a JSON file."""
    with open(output_file, 'w') as f:
        json.dump(comments_data, f, indent=2)
    
    # Print summary
    total_comments = (
        len(comments_data['issue_comments']) +
        len(comments_data['review_comments']) +
        len(comments_data['reviews'])
    )
    
    print(f"\nSummary for {comments_data['repo']} PR #{comments_data['pr_number']}:")
    print(f"  Issue comments: {len(comments_data['issue_comments'])}")
    print(f"  Review comments: {len(comments_data['review_comments'])}")
    print(f"  Reviews: {len(comments_data['reviews'])}")
    print(f"  Total: {total_comments}")
    print(f"\nSaved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Fetch all comments from a GitHub PR using gh CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch from current repo, auto-detect from git remote
  %(prog)s 149

  # Fetch from specific repo
  %(prog)s rshade/cronai 149
  
  # Fetch and save to custom file
  %(prog)s 149 --output my_comments.json
  
  # Fetch from different repo with custom output
  %(prog)s microsoft/vscode 12345 --output vscode_comments.json

Environment:
  Requires 'gh' CLI to be installed and authenticated.
  Set GITHUB_TOKEN environment variable if needed.
        """
    )
    
    parser.add_argument(
        'repo_or_pr',
        help='Repository name (owner/repo) or PR number if using current repo'
    )
    
    parser.add_argument(
        'pr_number',
        nargs='?',
        type=int,
        help='PR number (required if first arg is repo name)'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='github_comments.json',
        help='Output file path (default: github_comments.json)'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'summary'],
        default='json',
        help='Output format (default: json)'
    )
    
    args = parser.parse_args()
    
    # Parse arguments to determine repo and PR number
    if args.pr_number is not None:
        # Format: repo pr_number
        repo = args.repo_or_pr
        pr_number = args.pr_number
    else:
        # Format: pr_number (auto-detect repo)
        try:
            pr_number = int(args.repo_or_pr)
            repo = get_repo_from_remote()
            if not repo:
                print("Error: Could not detect repository from git remote.", file=sys.stderr)
                print("Please specify the repository explicitly: owner/repo pr_number", file=sys.stderr)
                sys.exit(1)
        except ValueError:
            print("Error: Invalid PR number or missing PR number argument.", file=sys.stderr)
            print("Usage: fetch_github_comments.py [repo] pr_number", file=sys.stderr)
            sys.exit(1)
    
    # Validate inputs
    if '/' not in repo:
        print("Error: Repository must be in format 'owner/repo'", file=sys.stderr)
        sys.exit(1)
    
    if pr_number <= 0:
        print("Error: PR number must be positive", file=sys.stderr)
        sys.exit(1)
    
    # Check if gh CLI is available
    try:
        subprocess.run(['gh', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: gh CLI is not installed or not in PATH", file=sys.stderr)
        print("Install from: https://cli.github.com/", file=sys.stderr)
        sys.exit(1)
    
    # Fetch comments
    try:
        comments_data = fetch_pr_comments(repo, pr_number)
        
        if args.format == 'summary':
            # Just print summary without saving
            total_comments = (
                len(comments_data['issue_comments']) +
                len(comments_data['review_comments']) +
                len(comments_data['reviews'])
            )
            print(f"Repo: {repo}")
            print(f"PR: #{pr_number}")
            print(f"Issue comments: {len(comments_data['issue_comments'])}")
            print(f"Review comments: {len(comments_data['review_comments'])}")
            print(f"Reviews: {len(comments_data['reviews'])}")
            print(f"Total: {total_comments}")
        else:
            save_comments(comments_data, args.output)
            
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()