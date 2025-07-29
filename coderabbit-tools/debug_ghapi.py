#!/usr/bin/env python3
"""
Debug script to examine the exact structure of CodeRabbit duplicate comments.
"""

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
            return None
    except FileNotFoundError:
        return None

def debug_duplicate_structure(owner, repo, pr_number, review_id):
    """Debug the exact structure of duplicate comments"""
    token = get_github_token()
    if not token:
        return
    
    api = GhApi(token=token)
    
    # Get the specific review
    review = api.pulls.get_review(owner, repo, pr_number, review_id)
    
    body = review.body
    print(f"Review body length: {len(body)}")
    print()
    
    # Find duplicate sections
    duplicate_pattern = r'<summary>♻️ Duplicate comments \((\d+)\)</summary>'
    matches = re.finditer(duplicate_pattern, body)
    
    for i, match in enumerate(matches):
        count = match.group(1)
        print(f"Duplicate section {i+1}: {count} comments")
        start_pos = match.start()
        
        # Find the end of this details section
        # Look for </details> that closes this duplicate section
        remaining = body[start_pos:]
        
        # Find blockquote content
        blockquote_start = remaining.find('<blockquote>')
        if blockquote_start == -1:
            print("  No blockquote found")
            continue
        
        # Find the matching closing blockquote
        blockquote_start += len('<blockquote>')
        blockquote_count = 1
        pos = blockquote_start
        
        while pos < len(remaining) and blockquote_count > 0:
            open_pos = remaining.find('<blockquote>', pos)
            close_pos = remaining.find('</blockquote>', pos)
            
            if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
                blockquote_count += 1
                pos = open_pos + len('<blockquote>')
            elif close_pos != -1:
                blockquote_count -= 1
                pos = close_pos + len('</blockquote>')
            else:
                break
        
        if blockquote_count == 0:
            blockquote_content = remaining[blockquote_start:pos - len('</blockquote>')]
            print(f"  Blockquote content length: {len(blockquote_content)}")
            
            # Show first part of content
            print(f"  First 500 chars:")
            print(f"    {repr(blockquote_content[:500])}")
            print()
            
            # Look for file sections
            file_pattern = r'<details>\s*<summary>([^<]+?)\s*\((\d+)\)</summary>'
            file_matches = re.findall(file_pattern, blockquote_content)
            print(f"  File sections found: {len(file_matches)}")
            for file_path, file_count in file_matches:
                print(f"    {file_path}: {file_count} issues")
            
            # If no file sections found, show the raw structure
            if not file_matches:
                print("  Raw content structure analysis:")
                lines = blockquote_content.split('\n')[:20]  # First 20 lines
                for j, line in enumerate(lines):
                    print(f"    {j+1:2d}: {repr(line)}")
            
        print()

def main():
    if len(sys.argv) < 5:
        print("Usage: debug_ghapi.py <owner> <repo> <pr_number> <review_id>")
        sys.exit(1)
    
    owner = sys.argv[1]
    repo = sys.argv[2] 
    pr_number = int(sys.argv[3])
    review_id = int(sys.argv[4])
    
    debug_duplicate_structure(owner, repo, pr_number, review_id)

if __name__ == '__main__':
    main()