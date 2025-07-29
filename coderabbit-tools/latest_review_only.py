#!/usr/bin/env python3
"""
Focus only on the latest CodeRabbit review to match their exact current count.
This avoids counting resolved/outdated issues from previous reviews.
"""

import subprocess
import sys
import re
from ghapi.all import GhApi

def get_github_token():
    """Get GitHub token using gh CLI"""
    try:
        result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        return None

def get_latest_coderabbit_issues(owner, repo, pr_number):
    """Get only current unresolved issues from the latest CodeRabbit review"""
    token = get_github_token()
    if not token:
        return []
    
    api = GhApi(token=token)
    
    # Get all reviews and find the latest CodeRabbit one
    reviews = api.pulls.list_reviews(owner, repo, pr_number)
    
    latest_review = None
    for review in reversed(reviews):  # Latest first
        if 'coderabbitai' in review.user.login.lower():
            latest_review = review
            break
    
    if not latest_review:
        print("No CodeRabbit reviews found")
        return []
    
    print(f"Latest CodeRabbit review: {latest_review.id}")
    
    body = latest_review.body
    
    # Extract counts from header
    actionable_match = re.search(r'\*\*Actionable comments posted: (\d+)\*\*', body)
    duplicate_match = re.search(r'♻️ Duplicate comments \((\d+)\)', body)
    
    actionable_count = int(actionable_match.group(1)) if actionable_match else 0
    duplicate_count = int(duplicate_match.group(1)) if duplicate_match else 0
    
    print(f"CodeRabbit reports: {actionable_count} actionable + {duplicate_count} duplicates = {actionable_count + duplicate_count} total")
    
    issues = []
    
    # Extract duplicate issues from this review only
    if duplicate_count > 0 and '♻️ Duplicate comments' in body:
        duplicate_start = body.find('<summary>♻️ Duplicate comments')
        if duplicate_start != -1:
            # Find the blockquote content
            blockquote_start = body.find('<blockquote>', duplicate_start)
            if blockquote_start != -1:
                blockquote_start += len('<blockquote>')
                blockquote_count = 1
                pos = blockquote_start
                
                # Find matching closing blockquote
                while pos < len(body) and blockquote_count > 0:
                    open_pos = body.find('<blockquote>', pos)
                    close_pos = body.find('</blockquote>', pos)
                    
                    if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
                        blockquote_count += 1
                        pos = open_pos + len('<blockquote>')
                    elif close_pos != -1:
                        blockquote_count -= 1
                        pos = close_pos + len('</blockquote>')
                    else:
                        break
                
                if blockquote_count == 0:
                    duplicate_content = body[blockquote_start:pos - len('</blockquote>')]
                    
                    # Parse file sections
                    file_pattern = r'<details>\s*<summary>([^<]+?)\s*\((\d+)\)</summary><blockquote>(.*?)</blockquote></details>'
                    file_matches = re.finditer(file_pattern, duplicate_content, re.DOTALL)
                    
                    for file_match in file_matches:
                        file_path = file_match.group(1).strip()
                        expected_count = int(file_match.group(2))
                        issue_content = file_match.group(3)
                        
                        # Parse individual issues
                        individual_issues = issue_content.split('\n---\n')
                        file_issues = []
                        
                        for individual_issue in individual_issues:
                            individual_issue = individual_issue.strip()
                            if not individual_issue:
                                continue
                            
                            # Extract line and title
                            line_pattern = r'`(\d+(?:-\d+)?)`: \*\*([^*]+)\*\*'
                            line_match = re.search(line_pattern, individual_issue)
                            
                            if line_match:
                                line_range = line_match.group(1)
                                title = line_match.group(2).strip()
                                start_line = int(line_range.split('-')[0]) if '-' in line_range else int(line_range)
                                
                                file_issues.append({
                                    'file': file_path,
                                    'line': start_line,
                                    'title': title,
                                    'source': 'duplicate'
                                })
                        
                        print(f"  {file_path}: {len(file_issues)}/{expected_count} issues")
                        issues.extend(file_issues)
    
    # Note: We're not adding actionable comments here since they would be 
    # new issues that aren't in the "duplicate" section
    
    print(f"\nExtracted {len(issues)} duplicate issues")
    print(f"Expected total (actionable + duplicates): {actionable_count + duplicate_count}")
    
    # The total should be actionable_count + len(issues)
    total_current = actionable_count + len(issues)
    expected_total = actionable_count + duplicate_count
    
    print(f"Our total: {actionable_count} actionable + {len(issues)} duplicates = {total_current}")
    print(f"Match: {'✅ YES' if total_current == expected_total else '❌ NO'}")
    
    return issues

def main():
    if len(sys.argv) < 4:
        print("Usage: latest_review_only.py <owner> <repo> <pr_number>")
        sys.exit(1)
    
    owner = sys.argv[1]
    repo = sys.argv[2] 
    pr_number = int(sys.argv[3])
    
    print(f"Getting current unresolved issues from latest CodeRabbit review for PR #{pr_number}...")
    print()
    
    issues = get_latest_coderabbit_issues(owner, repo, pr_number)
    
    if issues:
        print(f"\nCurrent unresolved duplicate issues:")
        for i, issue in enumerate(issues, 1):
            print(f"{i:2d}. {issue['file']}:{issue['line']} - {issue['title']}")

if __name__ == '__main__':
    main()