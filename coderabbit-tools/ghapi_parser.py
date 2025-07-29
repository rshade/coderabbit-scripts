#!/usr/bin/env python3
"""
Enhanced CodeRabbit comment parser using ghapi.
Attempts to parse all issues including duplicates more accurately.
"""

import json
import subprocess
import sys
import re
from ghapi.all import GhApi

def get_github_token():
    """Get GitHub token using gh CLI"""
    try:
        result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Error getting GitHub token: {result.stderr}", file=sys.stderr)
            return None
    except FileNotFoundError:
        print("gh CLI not found. Please install GitHub CLI or set GITHUB_TOKEN", file=sys.stderr)
        return None

def extract_duplicate_issues_advanced(review_body):
    """Advanced extraction of duplicate issues from CodeRabbit review body"""
    issues = []
    
    # Find duplicate sections using manual parsing (more robust than regex)
    duplicate_start = review_body.find('<summary>♻️ Duplicate comments')
    if duplicate_start == -1:
        return issues
    
    # Find the blockquote content
    blockquote_start = review_body.find('<blockquote>', duplicate_start)
    if blockquote_start == -1:
        return issues
    
    # Count nested blockquotes to find the correct closing
    blockquote_start += len('<blockquote>')
    blockquote_count = 1
    pos = blockquote_start
    
    while pos < len(review_body) and blockquote_count > 0:
        open_pos = review_body.find('<blockquote>', pos)
        close_pos = review_body.find('</blockquote>', pos)
        
        if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
            blockquote_count += 1
            pos = open_pos + len('<blockquote>')
        elif close_pos != -1:
            blockquote_count -= 1
            pos = close_pos + len('</blockquote>')
        else:
            break
    
    if blockquote_count != 0:
        return issues
    
    duplicate_content = review_body[blockquote_start:pos - len('</blockquote>')]
    
    # Extract count from header
    count_match = re.search(r'♻️ Duplicate comments \((\d+)\)', review_body)
    total_count = int(count_match.group(1)) if count_match else 0
    
    print(f"Processing duplicate section with {total_count} comments")
    print(f"Content length: {len(duplicate_content)}")
    
    # Find file sections within the duplicate content
    file_pattern = r'<details>\s*<summary>([^<]+?)\s*\((\d+)\)</summary><blockquote>(.*?)</blockquote></details>'
    file_matches = re.finditer(file_pattern, duplicate_content, re.DOTALL)
    
    for file_match in file_matches:
        file_path = file_match.group(1).strip()
        issue_count = int(file_match.group(2))
        issue_content = file_match.group(3)
        
        print(f"  File: {file_path} ({issue_count} issues)")
        
        # Parse individual issues within the file section
        # Split by '---' to separate issues
        individual_issues = issue_content.split('\n---\n')
        
        for i, individual_issue in enumerate(individual_issues):
            individual_issue = individual_issue.strip()
            if not individual_issue:
                continue
            
            # Try to extract line number and title
            line_pattern = r'`(\d+(?:-\d+)?)`: \*\*([^*]+)\*\*(.*?)(?=```|$)'
            line_match = re.search(line_pattern, individual_issue, re.DOTALL)
            
            if line_match:
                line_range = line_match.group(1)
                title = line_match.group(2).strip()
                description = line_match.group(3).strip()
                
                # Parse line number
                if '-' in line_range:
                    start_line = int(line_range.split('-')[0])
                else:
                    start_line = int(line_range)
                
                issues.append({
                    'file': file_path,
                    'line': start_line,
                    'title': title,
                    'description': description[:200] + '...' if len(description) > 200 else description,
                    'source': 'duplicate_comment'
                })
                
                print(f"    Issue {i+1}: Line {start_line} - {title}")
            else:
                # Try to extract general issues without line numbers
                general_pattern = r'\*\*([^*]+)\*\*(.*?)(?=\*\*|$)'
                general_match = re.search(general_pattern, individual_issue, re.DOTALL)
                
                if general_match:
                    title = general_match.group(1).strip()
                    description = general_match.group(2).strip()
                    
                    issues.append({
                        'file': file_path,
                        'line': None,
                        'title': title,
                        'description': description[:200] + '...' if len(description) > 200 else description,
                        'source': 'duplicate_comment'
                    })
                    
                    print(f"    General issue {i+1}: {title}")
                else:
                    print(f"    Could not parse issue {i+1}: {individual_issue[:100]}...")
    
    return issues

def extract_review_comments(api, owner, repo, pr_number):
    """Extract all review comments (line-specific)"""
    issues = []
    
    review_comments = api.pulls.list_review_comments(owner, repo, pr_number)
    for comment in review_comments:
        if 'coderabbitai' in comment.user.login.lower():
            # Check for actionable markers
            actionable_markers = [
                '_🛠️ Refactor suggestion_',
                '_⚠️ Potential issue_',
                '_💡 Suggestion_',
                '_🔒 Security issue_',
                '_🐛 Bug fix_',
                '_⚡ Performance issue_',
                '_📝 Documentation_',
                '_🧹 Cleanup_',
                '_🔧 Enhancement_',
                '_💡 Verification agent_',
                '_🧹 Nitpick (assertive)_'
            ]
            
            has_actionable_marker = any(marker in comment.body for marker in actionable_markers)
            if has_actionable_marker:
                issues.append({
                    'file': comment.path,
                    'line': comment.line,
                    'title': f"Review comment on {comment.path}",
                    'description': comment.body[:200] + '...' if len(comment.body) > 200 else comment.body,
                    'source': 'review_comment'
                })
    
    return issues

def main():
    if len(sys.argv) < 4:
        print("Usage: ghapi_parser.py <owner> <repo> <pr_number>")
        sys.exit(1)
    
    owner = sys.argv[1]
    repo = sys.argv[2] 
    pr_number = int(sys.argv[3])
    
    # Get GitHub token
    token = get_github_token()
    if not token:
        return
    
    # Initialize ghapi
    api = GhApi(token=token)
    
    print(f"Parsing PR #{pr_number} from {owner}/{repo} using ghapi...")
    print()
    
    all_issues = []
    
    # 1. Get review comments (line-specific)
    print("Extracting review comments...")
    review_issues = extract_review_comments(api, owner, repo, pr_number)
    all_issues.extend(review_issues)
    print(f"Found {len(review_issues)} review comment issues")
    print()
    
    # 2. Get duplicate issues from review bodies
    print("Extracting duplicate issues from review bodies...")
    reviews = api.pulls.list_reviews(owner, repo, pr_number)
    
    for review in reviews:
        if 'coderabbitai' in review.user.login.lower():
            if '♻️ Duplicate comments' in review.body:
                print(f"Processing review {review.id} with duplicate comments...")
                duplicate_issues = extract_duplicate_issues_advanced(review.body)
                all_issues.extend(duplicate_issues)
                print(f"Extracted {len(duplicate_issues)} duplicate issues")
                print()
    
    # 3. Remove duplicates based on file, line, and title
    unique_issues = []
    seen = set()
    
    for issue in all_issues:
        key = (issue['file'], issue.get('line'), issue['title'][:50])  # First 50 chars of title
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)
    
    print(f"Total issues found: {len(all_issues)}")
    print(f"Unique issues: {len(unique_issues)}")
    print()
    
    # Group by file for summary
    by_file = {}
    for issue in unique_issues:
        file_path = issue['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(issue)
    
    print("Issues by file:")
    total_count = 0
    for file_path, file_issues in sorted(by_file.items()):
        print(f"  {file_path}: {len(file_issues)} issues")
        total_count += len(file_issues)
        for issue in file_issues[:3]:  # Show first 3 issues per file
            line_info = f":{issue['line']}" if issue.get('line') else ""
            print(f"    - {issue['title']}{line_info}")
        if len(file_issues) > 3:
            print(f"    ... and {len(file_issues) - 3} more")
    
    print(f"\nTotal actionable issues: {total_count}")
    
    # Save detailed results
    output = {
        'pr_number': pr_number,
        'total_issues': len(all_issues),
        'unique_issues': len(unique_issues),
        'issues': unique_issues,
        'by_file': by_file
    }
    
    with open(f'ghapi_parsed_{pr_number}.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Detailed results saved to ghapi_parsed_{pr_number}.json")

if __name__ == '__main__':
    main()