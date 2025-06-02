#!/usr/bin/env python3
"""
Parse CodeRabbit comments from GitHub PR into AI-friendly format
"""
import json
import subprocess
import sys
import re

def get_pr_comments(pr_number, repo_name=None):
    """Fetch PR comments using gh CLI"""
    if not repo_name:
        # Try to detect repo from git remote
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
        except:
            pass
    
    if not repo_name:
        repo_name = "rshade/cronai"  # Default fallback
    
    # Get PR review comments
    cmd = ['gh', 'api', f'/repos/{repo_name}/pulls/{pr_number}/comments']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error fetching PR comments: {result.stderr}")
        return []
    
    return json.loads(result.stdout)

def get_pr_reviews(pr_number, repo_name=None):
    """Fetch PR reviews using gh CLI"""
    if not repo_name:
        # Try to detect repo from git remote
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
        except:
            pass
    
    if not repo_name:
        repo_name = "rshade/cronai"  # Default fallback
    
    cmd = ['gh', 'api', f'/repos/{repo_name}/pulls/{pr_number}/reviews']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return []
    
    return json.loads(result.stdout)

def parse_coderabbit_comment(comment):
    """Parse a CodeRabbit comment into AI-friendly format"""
    body = comment.get('body', '')
    
    # Skip non-CodeRabbit comments
    if 'coderabbitai' not in comment.get('user', {}).get('login', '').lower():
        return None
    
    # Extract file path and line
    path = comment.get('path', 'general')
    line = comment.get('line') or comment.get('original_line')
    
    # Extract suggestions
    suggestions = []
    if '```suggestion' in body:
        pattern = r'```suggestion(.*?)```'
        matches = re.findall(pattern, body, re.DOTALL)
        suggestions = [match.strip() for match in matches]
    
    # Extract actionable items
    action_patterns = [
        (r'Consider\s+(.*?)(?:\.|$)', 'refactor'),
        (r'It would be better to\s+(.*?)(?:\.|$)', 'improve'),
        (r'You should\s+(.*?)(?:\.|$)', 'fix'),
        (r'Please\s+(.*?)(?:\.|$)', 'update'),
        (r'Add\s+(.*?)(?:\.|$)', 'add'),
        (r'Include\s+(.*?)(?:\.|$)', 'add'),
        (r'Fix\s+(.*?)(?:\.|$)', 'fix'),
        (r'Update\s+(.*?)(?:\.|$)', 'update'),
        (r'Remove\s+(.*?)(?:\.|$)', 'remove'),
        (r'Replace\s+(.*?)(?:\.|$)', 'replace'),
        (r'Avoid\s+(.*?)(?:\.|$)', 'avoid'),
        (r'Use\s+(.*?)(?:\.|$)', 'use'),
    ]
    
    action = None
    action_type = 'general'
    
    for pattern, fix_type in action_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            action = match.group(1).strip()
            action = re.sub(r'\s+', ' ', action)
            action_type = fix_type
            break
    
    if not action:
        # Try to extract the main point from the comment
        lines = body.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('>', '#', '-', '*', '```')):
                action = line[:200]
                break
    
    if not action:
        return None
    
    return {
        'file': path,
        'line': line,
        'action': action,
        'type': action_type,
        'suggestions': suggestions,
        'full_comment': body[:500] + '...' if len(body) > 500 else body
    }

def format_ai_prompts(parsed_comments):
    """Format parsed comments into AI prompts"""
    prompts = []
    
    # Add instructions to avoid creating new CodeRabbit issues
    instructions = """
IMPORTANT: When making changes, be careful to avoid creating new issues that CodeRabbit will flag in aggressive mode:
- Avoid adding extra spaces or trailing whitespace
- Use consistent log levels (prefer log.Printf over logger.Printf unless specifically needed)
- Maintain consistent indentation and formatting
- Don't introduce unnecessary blank lines or remove necessary ones
- Keep existing code style and conventions
- Only make the specific changes requested, not additional "improvements"
"""
    
    for i, comment in enumerate(parsed_comments, 1):
        if not comment:
            continue
            
        prompt = f"Fix #{i} in {comment['file']}"
        if comment.get('line'):
            prompt += f" at line {comment['line']}"
        prompt += f": {comment['action']}"
        
        if comment.get('suggestions'):
            prompt += f"\n\nSuggested change:\n```\n{comment['suggestions'][0]}\n```"
        
        # Add the instructions to the first prompt
        if i == 1:
            prompt = instructions + "\n\n" + prompt
        
        prompts.append({
            'id': i,
            'prompt': prompt,
            'metadata': comment
        })
    
    return prompts

def format_for_cursor(prompts):
    """Format prompts for Cursor AI"""
    cursor_tasks = []
    
    for prompt in prompts:
        task = f"[Task {prompt['id']}] {prompt['prompt']}"
        cursor_tasks.append(task)
    
    return cursor_tasks

def main(pr_number, repo_name=None):
    print(f"Fetching CodeRabbit comments for PR #{pr_number}...")
    
    # Get all PR comments
    comments = get_pr_comments(pr_number, repo_name)
    reviews = get_pr_reviews(pr_number, repo_name)
    
    # Parse CodeRabbit comments
    parsed = []
    
    for comment in comments:
        parsed_comment = parse_coderabbit_comment(comment)
        if parsed_comment:
            parsed.append(parsed_comment)
    
    # Also check review comments
    for review in reviews:
        if 'coderabbitai' in review.get('user', {}).get('login', '').lower():
            body = review.get('body', '')
            parsed_comment = parse_coderabbit_comment({'body': body, 'path': 'general', 'user': review.get('user')})
            if parsed_comment:
                parsed.append(parsed_comment)
    
    # Format into AI prompts
    ai_prompts = format_ai_prompts(parsed)
    cursor_format = format_for_cursor(ai_prompts)
    
    # Output
    output = {
        'pr_number': pr_number,
        'total_fixes': len(ai_prompts),
        'prompts': [p['prompt'] for p in ai_prompts],
        'cursor_format': cursor_format,
        'detailed_prompts': ai_prompts
    }
    
    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: coderabbit_ai_formatter.py <pr_number> [repo_name]")
        sys.exit(1)
    
    pr_number = int(sys.argv[1])
    repo_name = sys.argv[2] if len(sys.argv) > 2 else None
    main(pr_number, repo_name)