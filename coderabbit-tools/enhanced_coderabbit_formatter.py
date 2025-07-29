#!/usr/bin/env python3
"""
Enhanced CodeRabbit comment parser using GhApi for accurate issue detection.
Only processes the latest reviews to avoid resolved/outdated comments.
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
        return result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        print("Error: gh CLI not found. Please install GitHub CLI.", file=sys.stderr)
        return None

def detect_repo_from_git():
    """Detect repository from git remote"""
    try:
        result = subprocess.run(['git', 'config', '--get', 'remote.origin.url'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            remote_url = result.stdout.strip()
            if 'github.com' in remote_url:
                # Extract repo name from URL
                if remote_url.endswith('.git'):
                    remote_url = remote_url[:-4]
                repo_name = '/'.join(remote_url.split('/')[-2:])
                if repo_name.startswith('git@github.com:'):
                    repo_name = repo_name[15:]
                elif 'github.com/' in repo_name:
                    repo_name = repo_name.split('github.com/')[-1]
                return repo_name
    except:
        pass
    return None

def get_latest_coderabbit_review(api, owner, repo, pr_number):
    """Get the latest CodeRabbit review to avoid resolved/outdated comments"""
    reviews = api.pulls.list_reviews(owner, repo, pr_number)
    
    latest_review = None
    for review in reversed(reviews):  # Latest first
        if 'coderabbitai' in review.user.login.lower():
            latest_review = review
            break
    
    return latest_review

def get_latest_copilot_comments(api, owner, repo, pr_number, include_review_summaries=False):
    """Get non-outdated Copilot review comments (line-specific only for now)"""
    copilot_comments = []
    
    # 1. Get individual review comments from Copilot
    review_comments = api.pulls.list_review_comments(owner, repo, pr_number)
    
    for comment in review_comments:
        if 'copilot' in comment.user.login.lower():
            # Skip outdated comments (those with outdated flag or resolved status)
            if hasattr(comment, 'in_reply_to_id') and comment.in_reply_to_id:
                continue  # Skip reply comments
            
            copilot_comments.append({
                'file': getattr(comment, 'path', 'unknown'),
                'line': getattr(comment, 'line', None),
                'title': 'Copilot suggestion',
                'description': comment.body[:500] + '...' if len(comment.body) > 500 else comment.body,
                'source': 'copilot_comment',
                'id': getattr(comment, 'id', None),
                'created_at': getattr(comment, 'created_at', 'unknown')
            })
    
    # 2. Get Copilot reviews and extract suggestions from review bodies
    # NOTE: Currently disabled - Copilot review summaries are typically low confidence
    # and more informational than actionable. Enable this later when we have better
    # filtering for high-confidence actionable suggestions.
    if include_review_summaries:
        reviews = api.pulls.list_reviews(owner, repo, pr_number)
        
        for review in reviews:
            if 'copilot' in review.user.login.lower() and review.body:
                # Extract actionable suggestions from Copilot review body
                suggestions = extract_copilot_suggestions_from_review(review.body)
                for suggestion in suggestions:
                    suggestion['source'] = 'copilot_review'
                    suggestion['review_id'] = review.id
                    copilot_comments.append(suggestion)
    
    return copilot_comments

def extract_copilot_suggestions_from_review(review_body):
    """Extract actionable suggestions from Copilot review body"""
    suggestions = []
    
    # Look for sections that contain actionable suggestions
    # Copilot often structures reviews with headers and suggestions
    
    # Pattern 1: Look for bullet points or numbered lists with suggestions
    suggestion_patterns = [
        r'[-*•]\s+(.+?)(?=\n[-*•]|\n\n|\n$)',  # Bullet points
        r'\d+\.\s+(.+?)(?=\n\d+\.|\n\n|\n$)',  # Numbered lists
        r'##\s+(.+?)\n\n(.+?)(?=\n##|\n\n##|$)',  # Headers with content
        r'### (.+?)\n\n(.+?)(?=\n###|\n\n###|$)',  # Sub-headers with content
    ]
    
    # Look for actionable keywords that indicate suggestions
    actionable_keywords = [
        'consider', 'should', 'recommend', 'suggest', 'improve', 'fix', 
        'add', 'remove', 'update', 'refactor', 'replace', 'implement',
        'security', 'vulnerability', 'error', 'issue', 'problem'
    ]
    
    for pattern in suggestion_patterns:
        matches = re.finditer(pattern, review_body, re.DOTALL | re.IGNORECASE)
        for match in matches:
            if len(match.groups()) == 1:
                suggestion_text = match.group(1).strip()
            else:
                title = match.group(1).strip()
                suggestion_text = match.group(2).strip()
            
            # Check if this looks like an actionable suggestion
            lower_text = suggestion_text.lower()
            if any(keyword in lower_text for keyword in actionable_keywords):
                # Try to extract file references
                file_pattern = r'`([^`]+\.(go|js|ts|py|md|yaml|yml|json))`'
                file_matches = re.findall(file_pattern, suggestion_text)
                
                if file_matches:
                    for file_match, ext in file_matches:
                        suggestions.append({
                            'file': file_match,
                            'line': None,
                            'title': f"Copilot suggestion for {file_match}",
                            'description': suggestion_text[:300] + '...' if len(suggestion_text) > 300 else suggestion_text,
                            'detailed_instruction': suggestion_text if len(suggestion_text) > 50 else None
                        })
                else:
                    # General suggestion without specific file
                    suggestions.append({
                        'file': 'general',
                        'line': None,
                        'title': 'Copilot general suggestion',
                        'description': suggestion_text[:300] + '...' if len(suggestion_text) > 300 else suggestion_text,
                        'detailed_instruction': suggestion_text if len(suggestion_text) > 50 else None
                    })
    
    return suggestions

def extract_duplicate_issues_from_review(review_body):
    """Extract duplicate issues from CodeRabbit review body using proven parsing logic"""
    issues = []
    
    if '♻️ Duplicate comments' not in review_body:
        return issues
    
    # Find duplicate section
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
    
    # Parse file sections
    file_pattern = r'<details>\s*<summary>([^<]+?)\s*\((\d+)\)</summary><blockquote>(.*?)</blockquote></details>'
    file_matches = re.finditer(file_pattern, duplicate_content, re.DOTALL)
    
    for file_match in file_matches:
        file_path = file_match.group(1).strip()
        issue_content = file_match.group(3)
        
        # Parse individual issues
        individual_issues = issue_content.split('\n---\n')
        
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
                
                # Extract detailed instruction if available
                instruction = extract_detailed_instruction(individual_issue)
                
                issues.append({
                    'file': file_path,
                    'line': start_line,
                    'title': title,
                    'description': individual_issue[:300] + '...' if len(individual_issue) > 300 else individual_issue,
                    'detailed_instruction': instruction,
                    'source': 'duplicate_comment'
                })
    
    return issues

def get_actionable_review_comments(api, owner, repo, pr_number, latest_review_id):
    """Get actionable review comments from the latest review"""
    issues = []
    
    try:
        review_comments = api.pulls.list_comments_for_review(owner, repo, pr_number, latest_review_id)
    except:
        # Fallback to all review comments if specific review API fails
        review_comments = api.pulls.list_review_comments(owner, repo, pr_number)
        # Filter to only CodeRabbit comments
        review_comments = [c for c in review_comments if 'coderabbitai' in c.user.login.lower()]
    
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
    
    for comment in review_comments:
        if any(marker in comment.body for marker in actionable_markers):
            # Extract detailed instruction
            instruction = extract_detailed_instruction(comment.body)
            
            issues.append({
                'file': getattr(comment, 'path', 'unknown'),
                'line': getattr(comment, 'line', None),
                'title': extract_title_from_comment(comment.body),
                'description': comment.body[:500] + '...' if len(comment.body) > 500 else comment.body,
                'detailed_instruction': instruction,
                'source': 'actionable_comment',
                'id': getattr(comment, 'id', None)
            })
    
    return issues

def extract_title_from_comment(body):
    """Extract title from comment body"""
    # Look for bold text after markers
    title_patterns = [
        r'_[^_]+_\s*\n\s*\*\*([^*]+)\*\*',
        r'\*\*([^*]+)\*\*',
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, body)
        if match:
            return match.group(1).strip()
    
    # Fallback: use first line
    first_line = body.split('\n')[0].strip()
    return first_line[:100] + '...' if len(first_line) > 100 else first_line

def extract_detailed_instruction(body):
    """Extract detailed instructions from comment body, including AI Agent prompts"""
    
    # Look for "Prompt for AI Agents" section specifically
    ai_prompt_pattern = r'<summary>🤖 Prompt for AI Agents</summary>\s*```(.*?)```'
    ai_prompt_match = re.search(ai_prompt_pattern, body, re.DOTALL)
    if ai_prompt_match:
        return ai_prompt_match.group(1).strip()
    
    # Look for collapsible details sections
    details_patterns = [
        r'<summary>🤖 Prompt for AI Agents</summary>\s*(.*?)(?=</details>|$)',
        r'<details>\s*<summary>.*?</summary>\s*(.*?)(?=</details>|$)',
        r'```\s*(In [^`]+around lines [^`]+.*?)```',  # Match "In file around lines X to Y, ..."
    ]
    
    for pattern in details_patterns:
        match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
        if match:
            instruction = match.group(1).strip()
            # Clean up HTML tags and markdown
            instruction = re.sub(r'<[^>]+>', '', instruction)
            instruction = re.sub(r'```[^`]*```', '', instruction)
            instruction = re.sub(r'\s+', ' ', instruction).strip()
            if len(instruction) > 50:  # Only use if substantial
                return instruction
    
    return None

def get_enhanced_pr_issues(owner, repo, pr_number):
    """Get all current issues from latest reviews only, avoiding resolved/outdated comments"""
    token = get_github_token()
    if not token:
        print("Error: Could not get GitHub token", file=sys.stderr)
        return []
    
    api = GhApi(token=token)
    
    print(f"Analyzing PR #{pr_number} from {owner}/{repo} using enhanced parser...")
    
    all_issues = []
    
    # 1. Get latest CodeRabbit review and extract both actionable and duplicate issues
    latest_review = get_latest_coderabbit_review(api, owner, repo, pr_number)
    
    if latest_review:
        print(f"Found latest CodeRabbit review: {latest_review.id}")
        
        # Extract counts from review body for verification
        actionable_match = re.search(r'\*\*Actionable comments posted: (\d+)\*\*', latest_review.body)
        duplicate_match = re.search(r'♻️ Duplicate comments \((\d+)\)', latest_review.body)
        
        actionable_count = int(actionable_match.group(1)) if actionable_match else 0
        duplicate_count = int(duplicate_match.group(1)) if duplicate_match else 0
        
        print(f"CodeRabbit reports: {actionable_count} actionable + {duplicate_count} duplicates = {actionable_count + duplicate_count} total")
        
        # Get actionable comments from this review
        actionable_issues = get_actionable_review_comments(api, owner, repo, pr_number, latest_review.id)
        all_issues.extend(actionable_issues)
        print(f"Extracted {len(actionable_issues)} actionable issues")
        
        # Get duplicate issues from review body
        duplicate_issues = extract_duplicate_issues_from_review(latest_review.body)
        all_issues.extend(duplicate_issues)
        print(f"Extracted {len(duplicate_issues)} duplicate issues")
        
        # Verification
        total_extracted = len(actionable_issues) + len(duplicate_issues)
        expected_total = actionable_count + duplicate_count
        
        print(f"Verification: Expected {expected_total}, extracted {total_extracted}")
        if total_extracted == expected_total:
            print("✅ Perfect match with CodeRabbit's count!")
        else:
            print(f"⚠️  Count mismatch (difference: {total_extracted - expected_total})")
    
    # 2. Get non-outdated Copilot comments
    copilot_issues = get_latest_copilot_comments(api, owner, repo, pr_number)
    all_issues.extend(copilot_issues)
    if copilot_issues:
        print(f"Extracted {len(copilot_issues)} Copilot issues")
    
    # 3. Remove exact duplicates based on file, line, and title
    unique_issues = []
    seen = set()
    
    for issue in all_issues:
        key = (issue['file'], issue.get('line'), issue['title'][:50])
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)
    
    print(f"\nTotal issues: {len(all_issues)}, unique: {len(unique_issues)}")
    
    return unique_issues

def format_issues_for_ai(issues, pr_number):
    """Format issues into AI-friendly prompts"""
    if not issues:
        return {"pr_number": pr_number, "total_fixes": 0, "prompts": []}
    
    prompts = []
    
    # Group issues by priority and type
    high_priority = [i for i in issues if i['source'] in ['actionable_comment'] and 
                    any(marker in i.get('description', '') for marker in ['⚠️ Potential issue', '🔒 Security issue'])]
    
    medium_priority = [i for i in issues if i['source'] in ['duplicate_comment', 'actionable_comment'] and i not in high_priority]
    
    low_priority = [i for i in issues if i['source'] == 'copilot_comment']
    
    # Create AI prompts for each issue
    for priority_group, priority_name in [(high_priority, "HIGH"), (medium_priority, "MEDIUM"), (low_priority, "LOW")]:
        for i, issue in enumerate(priority_group, 1):
            detailed_instruction = issue.get('detailed_instruction')
            if detailed_instruction:
                prompt = f"""
🔧 TASK #{len(prompts) + 1}: {issue['file']}:line {issue.get('line', 'unknown')} [PRIORITY: {priority_name}]

📝 ISSUE: {detailed_instruction}

✅ EXECUTION REQUIREMENTS:
1. Read the entire file {issue['file']} to understand context
2. Make ONLY the specific change required to fix this issue
3. Run validation: make lint && make validate && make test
4. Fix any validation failures immediately
5. Ensure change addresses the specific issue described

🚫 DO NOT:
- Make unrelated changes
- Add unnecessary imports or formatting
- Proceed if validation fails

🎯 SUCCESS CRITERIA:
- Issue is fixed exactly as described
- All validation passes
- No new issues introduced

SOURCE: {issue['source']} | FILE: {issue['file']}:{issue.get('line', '?')}
"""
            else:
                prompt = f"""
🔧 TASK #{len(prompts) + 1}: {issue['file']}:line {issue.get('line', 'unknown')} [PRIORITY: {priority_name}]

📝 ISSUE: {issue['title']}
{issue.get('description', '')[:300]}...

✅ EXECUTION REQUIREMENTS:
1. Read the entire file {issue['file']} to understand context
2. Analyze the issue and determine the appropriate fix
3. Make the minimal change required
4. Run validation: make lint && make validate && make test

SOURCE: {issue['source']} | FILE: {issue['file']}:{issue.get('line', '?')}
"""
            
            prompts.append(prompt.strip())
    
    return {
        "pr_number": pr_number,
        "total_fixes": len(issues),
        "issues": issues,
        "prompts": prompts,
        "high_priority_count": len(high_priority),
        "medium_priority_count": len(medium_priority),
        "low_priority_count": len(low_priority)
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: enhanced_coderabbit_formatter.py <pr_number> [owner/repo]")
        sys.exit(1)
    
    pr_number = int(sys.argv[1])
    
    if len(sys.argv) >= 3:
        repo_name = sys.argv[2]
        if '/' in repo_name:
            owner, repo = repo_name.split('/', 1)
        else:
            print("Error: Repository must be in format 'owner/repo'")
            sys.exit(1)
    else:
        # Auto-detect from git
        repo_name = detect_repo_from_git()
        if not repo_name:
            print("Error: Could not detect repository. Please specify owner/repo")
            sys.exit(1)
        owner, repo = repo_name.split('/', 1)
    
    print(f"Processing PR #{pr_number} from {owner}/{repo}")
    
    # Get all current issues
    issues = get_enhanced_pr_issues(owner, repo, pr_number)
    
    if not issues:
        print("No current issues found to fix")
        return
    
    # Format for AI
    result = format_issues_for_ai(issues, pr_number)
    
    # Output results
    print(f"\n📊 SUMMARY:")
    print(f"Total issues: {result['total_fixes']}")
    print(f"High priority: {result['high_priority_count']}")
    print(f"Medium priority: {result['medium_priority_count']}")
    print(f"Low priority: {result['low_priority_count']}")
    
    # Save detailed results
    output_file = f'enhanced_analysis_{pr_number}.json'
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nDetailed analysis saved to {output_file}")
    print("\n" + "="*60)
    print("AI-FORMATTED PROMPTS:")
    print("="*60)
    for prompt in result['prompts']:
        print(prompt)
        print("-" * 60)

if __name__ == '__main__':
    main()