#!/usr/bin/env python3
"""
Test script using ghapi to parse GitHub pull request comments.
Compare with existing coderabbit_ai_formatter.py approach.
"""

import json
import subprocess
import sys
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

def test_ghapi_pr_parsing(owner, repo, pr_number):
    """Test ghapi for parsing PR comments and reviews"""
    
    # Get GitHub token
    token = get_github_token()
    if not token:
        print("Could not get GitHub token", file=sys.stderr)
        return None
    
    # Initialize ghapi
    api = GhApi(token=token)
    
    try:
        print(f"Fetching PR #{pr_number} from {owner}/{repo}...")
        
        # Get basic PR info
        pr = api.pulls.get(owner, repo, pr_number)
        print(f"PR Title: {pr.title}")
        print(f"PR State: {pr.state}")
        print(f"Comments: {pr.comments}")
        print(f"Review Comments: {pr.review_comments}")
        print()
        
        # Get different types of comments
        results = {
            'pr_info': {
                'number': pr.number,
                'title': pr.title,
                'state': pr.state,
                'comment_count': pr.comments,
                'review_comment_count': pr.review_comments
            },
            'issue_comments': [],
            'review_comments': [],
            'reviews': []
        }
        
        # 1. Get issue comments (general PR comments)
        print("Fetching issue comments...")
        issue_comments = api.issues.list_comments(owner, repo, pr_number)
        for comment in issue_comments:
            if 'coderabbitai' in comment.user.login.lower():
                results['issue_comments'].append({
                    'id': comment.id,
                    'user': comment.user.login,
                    'created_at': str(comment.created_at),
                    'body_preview': comment.body[:200] + '...' if len(comment.body) > 200 else comment.body,
                    'body_length': len(comment.body),
                    'has_duplicate_section': '♻️ Duplicate comments' in comment.body
                })
        
        print(f"Found {len(results['issue_comments'])} CodeRabbit issue comments")
        
        # 2. Get review comments (line-specific comments)
        print("Fetching review comments...")
        review_comments = api.pulls.list_review_comments(owner, repo, pr_number)
        for comment in review_comments:
            if 'coderabbitai' in comment.user.login.lower():
                results['review_comments'].append({
                    'id': comment.id,
                    'user': comment.user.login,
                    'path': comment.path,
                    'line': comment.line,
                    'created_at': str(comment.created_at),
                    'body_preview': comment.body[:200] + '...' if len(comment.body) > 200 else comment.body,
                    'body_length': len(comment.body)
                })
        
        print(f"Found {len(results['review_comments'])} CodeRabbit review comments")
        
        # 3. Get PR reviews (review summaries)
        print("Fetching PR reviews...")
        reviews = api.pulls.list_reviews(owner, repo, pr_number)
        for review in reviews:
            if 'coderabbitai' in review.user.login.lower():
                results['reviews'].append({
                    'id': review.id,
                    'user': review.user.login,
                    'state': review.state,
                    'created_at': str(getattr(review, 'created_at', 'unknown')),
                    'body_preview': review.body[:200] + '...' if len(review.body) > 200 else review.body,
                    'body_length': len(review.body),
                    'has_duplicate_section': '♻️ Duplicate comments' in review.body
                })
        
        print(f"Found {len(results['reviews'])} CodeRabbit reviews")
        
        return results
        
    except Exception as e:
        print(f"Error fetching PR data: {e}", file=sys.stderr)
        return None

def analyze_duplicate_comments(results):
    """Analyze reviews with duplicate comments sections"""
    if not results:
        return
    
    print("\n" + "="*60)
    print("ANALYZING DUPLICATE COMMENTS SECTIONS")
    print("="*60)
    
    # Look for reviews with duplicate comments
    reviews_with_duplicates = [r for r in results['reviews'] if r['has_duplicate_section']]
    issue_comments_with_duplicates = [r for r in results['issue_comments'] if r['has_duplicate_section']]
    
    print(f"Reviews with duplicate sections: {len(reviews_with_duplicates)}")
    print(f"Issue comments with duplicate sections: {len(issue_comments_with_duplicates)}")
    
    for i, review in enumerate(reviews_with_duplicates):
        print(f"\nReview #{i+1} (ID: {review['id']}):")
        print(f"  State: {review['state']}")
        print(f"  Body length: {review['body_length']}")
        print(f"  Created: {review['created_at']}")
        print(f"  Preview: {review['body_preview']}")

def detailed_duplicate_analysis(owner, repo, pr_number, review_id):
    """Get detailed analysis of a specific review with duplicate comments"""
    token = get_github_token()
    if not token:
        return None
    
    api = GhApi(token=token)
    
    try:
        # Get the full review
        review = api.pulls.get_review(owner, repo, pr_number, review_id)
        
        print(f"\n" + "="*60)
        print(f"DETAILED ANALYSIS OF REVIEW {review_id}")
        print("="*60)
        
        body = review.body
        print(f"Full body length: {len(body)}")
        
        # Look for duplicate comments section
        if '♻️ Duplicate comments' in body:
            print("Found duplicate comments section!")
            
            # Find the section
            import re
            pattern = r'<summary>♻️ Duplicate comments \((\d+)\)</summary>'
            match = re.search(pattern, body)
            if match:
                count = match.group(1)
                print(f"Duplicate count in header: {count}")
                
                # Extract the section more carefully
                start_pos = body.find('<summary>♻️ Duplicate comments')
                if start_pos != -1:
                    # Find the end of this details section
                    # Look for the next </details> that closes this section
                    remaining = body[start_pos:]
                    
                    # Simple approach: find </details> after </blockquote>
                    blockquote_end = remaining.find('</blockquote></details>')
                    if blockquote_end != -1:
                        duplicate_section = remaining[:blockquote_end + len('</blockquote></details>')]
                        print(f"Extracted duplicate section length: {len(duplicate_section)}")
                        
                        # Count individual file sections
                        file_pattern = r'<details>\s*<summary>([^<]+?)\s*\((\d+)\)</summary>'
                        file_matches = re.findall(file_pattern, duplicate_section)
                        print(f"Found {len(file_matches)} file sections:")
                        
                        total_issues = 0
                        for file_path, issue_count in file_matches:
                            print(f"  {file_path}: {issue_count} issues")
                            total_issues += int(issue_count)
                        
                        print(f"Total issues in duplicate section: {total_issues}")
                        
                        return {
                            'duplicate_section': duplicate_section,
                            'file_sections': file_matches,
                            'total_issues': total_issues
                        }
        
        return None
        
    except Exception as e:
        print(f"Error analyzing review: {e}", file=sys.stderr)
        return None

def main():
    if len(sys.argv) < 4:
        print("Usage: test_ghapi.py <owner> <repo> <pr_number> [review_id]")
        sys.exit(1)
    
    owner = sys.argv[1]
    repo = sys.argv[2] 
    pr_number = int(sys.argv[3])
    
    # Test basic parsing
    results = test_ghapi_pr_parsing(owner, repo, pr_number)
    if results:
        # Save results to file for comparison
        with open(f'ghapi_results_{pr_number}.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to ghapi_results_{pr_number}.json")
        
        # Analyze duplicate comments
        analyze_duplicate_comments(results)
        
        # If a specific review ID is provided, do detailed analysis
        if len(sys.argv) > 4:
            review_id = int(sys.argv[4])
            detailed_analysis = detailed_duplicate_analysis(owner, repo, pr_number, review_id)
            if detailed_analysis:
                print(f"\nDetailed analysis completed. Found {detailed_analysis['total_issues']} total issues.")

if __name__ == '__main__':
    main()