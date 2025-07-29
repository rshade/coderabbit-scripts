#!/usr/bin/env python3
"""
Match the exact CodeRabbit count for the latest review.
Focus on the most recent review to match "1 actionable + 16 duplicates = 17 total"
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

def analyze_latest_review(owner, repo, pr_number):
    """Analyze the latest CodeRabbit review to match their exact count"""
    token = get_github_token()
    if not token:
        return
    
    api = GhApi(token=token)
    
    # Get all reviews and find the latest CodeRabbit one
    reviews = api.pulls.list_reviews(owner, repo, pr_number)
    
    latest_coderabbit_review = None
    for review in reversed(reviews):  # Get latest first
        if 'coderabbitai' in review.user.login.lower():
            latest_coderabbit_review = review
            break
    
    if not latest_coderabbit_review:
        print("No CodeRabbit reviews found")
        return
    
    print(f"Analyzing latest CodeRabbit review: {latest_coderabbit_review.id}")
    print(f"Review state: {latest_coderabbit_review.state}")
    print()
    
    body = latest_coderabbit_review.body
    
    # Extract the counts from the header
    actionable_match = re.search(r'\*\*Actionable comments posted: (\d+)\*\*', body)
    duplicate_match = re.search(r'♻️ Duplicate comments \((\d+)\)', body)
    
    actionable_count = int(actionable_match.group(1)) if actionable_match else 0
    duplicate_count = int(duplicate_match.group(1)) if duplicate_match else 0
    total_expected = actionable_count + duplicate_count
    
    print(f"CodeRabbit reported counts:")
    print(f"  Actionable comments: {actionable_count}")
    print(f"  Duplicate comments: {duplicate_count}")
    print(f"  Total expected: {total_expected}")
    print()
    
    # Now extract the actual issues using our parser
    issues = []
    
    # 1. Get actionable review comments from this review specifically
    # Find review comments that were posted as part of this review
    review_comments = api.pulls.list_comments_for_review(owner, repo, pr_number, latest_coderabbit_review.id)
    
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
    
    actionable_issues = []
    for comment in review_comments:
        if any(marker in comment.body for marker in actionable_markers):
            actionable_issues.append({
                'file': comment.path,
                'line': comment.line,
                'title': f"Actionable comment",
                'source': 'review_comment',
                'id': comment.id
            })
    
    print(f"Found {len(actionable_issues)} actionable review comments")
    
    # 2. Extract duplicate issues from the review body
    duplicate_issues = []
    if '♻️ Duplicate comments' in body:
        # Use the same parsing logic as before
        duplicate_start = body.find('<summary>♻️ Duplicate comments')
        if duplicate_start != -1:
            blockquote_start = body.find('<blockquote>', duplicate_start)
            if blockquote_start != -1:
                blockquote_start += len('<blockquote>')
                blockquote_count = 1
                pos = blockquote_start
                
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
                    
                    # Find file sections
                    file_pattern = r'<details>\s*<summary>([^<]+?)\s*\((\d+)\)</summary><blockquote>(.*?)</blockquote></details>'
                    file_matches = re.finditer(file_pattern, duplicate_content, re.DOTALL)
                    
                    for file_match in file_matches:
                        file_path = file_match.group(1).strip()
                        issue_count = int(file_match.group(2))
                        issue_content = file_match.group(3)
                        
                        # Split by '---' to get individual issues
                        individual_issues = issue_content.split('\n---\n')
                        
                        for i, individual_issue in enumerate(individual_issues):
                            individual_issue = individual_issue.strip()
                            if not individual_issue:
                                continue
                            
                            # Extract line number and title
                            line_pattern = r'`(\d+(?:-\d+)?)`: \*\*([^*]+)\*\*'
                            line_match = re.search(line_pattern, individual_issue)
                            
                            if line_match:
                                line_range = line_match.group(1)
                                title = line_match.group(2).strip()
                                start_line = int(line_range.split('-')[0]) if '-' in line_range else int(line_range)
                                
                                duplicate_issues.append({
                                    'file': file_path,
                                    'line': start_line,
                                    'title': title,
                                    'source': 'duplicate_comment'
                                })
    
    print(f"Found {len(duplicate_issues)} duplicate issues")
    print()
    
    # Summary
    total_found = len(actionable_issues) + len(duplicate_issues)
    print(f"Extraction results:")
    print(f"  Actionable issues found: {len(actionable_issues)}")
    print(f"  Duplicate issues found: {len(duplicate_issues)}")
    print(f"  Total found: {total_found}")
    print(f"  Expected total: {total_expected}")
    print(f"  Match: {'✅ YES' if total_found == total_expected else '❌ NO'}")
    
    if total_found == total_expected:
        print(f"\n🎉 Perfect match! We found exactly {total_expected} issues as reported by CodeRabbit.")
    else:
        print(f"\n⚠️  Mismatch. Expected {total_expected} but found {total_found}")
        print(f"   Difference: {total_found - total_expected}")
    
    # Show breakdown by file for duplicates
    if duplicate_issues:
        print(f"\nDuplicate issues by file:")
        by_file = {}
        for issue in duplicate_issues:
            file_path = issue['file']
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(issue)
        
        for file_path, file_issues in by_file.items():
            print(f"  {file_path}: {len(file_issues)} issues")

def main():
    if len(sys.argv) < 4:
        print("Usage: match_coderabbit_count.py <owner> <repo> <pr_number>")
        sys.exit(1)
    
    owner = sys.argv[1]
    repo = sys.argv[2] 
    pr_number = int(sys.argv[3])
    
    analyze_latest_review(owner, repo, pr_number)

if __name__ == '__main__':
    main()