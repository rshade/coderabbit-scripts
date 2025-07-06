#!/usr/bin/env python3
"""
Optimized CodeRabbit AI Formatter - Direct GitHub API to AI prompts
This script bypasses the fetch/parse/apply pipeline and goes directly to AI formatting.
"""

import argparse
import subprocess
import sys
import json
import re
from typing import List, Dict, Optional


def get_repo_info() -> str:
    """Auto-detect repository from git remote."""
    try:
        result = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'], 
            capture_output=True, text=True, check=True
        )
        remote_url = result.stdout.strip()
        if 'github.com' in remote_url:
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
    return "rshade/cronai"  # Default fallback


def fetch_pr_data(pr_number: int, repo_name: str) -> Dict:
    """Fetch both PR comments and reviews in parallel."""
    import concurrent.futures
    
    def fetch_comments():
        cmd = ['gh', 'api', f'/repos/{repo_name}/pulls/{pr_number}/comments']
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout) if result.returncode == 0 else []
    
    def fetch_reviews():
        cmd = ['gh', 'api', f'/repos/{repo_name}/pulls/{pr_number}/reviews']
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout) if result.returncode == 0 else []
    
    # Fetch in parallel for speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        comments_future = executor.submit(fetch_comments)
        reviews_future = executor.submit(fetch_reviews)
        
        comments = comments_future.result()
        reviews = reviews_future.result()
    
    return {'comments': comments, 'reviews': reviews}


def is_coderabbit_comment(comment: Dict) -> bool:
    """Quick check if comment is from CodeRabbit."""
    user = comment.get('user', {})
    login = user.get('login', '').lower()
    return 'coderabbit' in login or 'coderabbitai' in login


def extract_actionable_content(body: str) -> Optional[Dict]:
    """Extract actionable content from CodeRabbit comment body."""
    if not body or len(body.strip()) < 10:
        return None
    
    # Quick patterns for actionable content
    action_indicators = [
        r'Consider\s+(.+?)(?:\.|$)',
        r'(?:Please|Should|Must|Need to)\s+(.+?)(?:\.|$)',
        r'(?:Add|Remove|Update|Fix|Replace|Avoid|Use)\s+(.+?)(?:\.|$)',
        r'It would be better to\s+(.+?)(?:\.|$)',
        r'Recommend\s+(.+?)(?:\.|$)'
    ]
    
    # Extract suggestions (highest priority)
    suggestions = []
    if '```suggestion' in body:
        suggestions = re.findall(r'```suggestion(.*?)```', body, re.DOTALL)
    
    # Find actionable text
    action_text = None
    action_type = 'general'
    
    for pattern in action_indicators:
        match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
        if match:
            action_text = match.group(1).strip()
            action_text = re.sub(r'\s+', ' ', action_text)[:150]  # Limit length
            if 'consider' in pattern.lower():
                action_type = 'refactor'
            elif any(word in pattern.lower() for word in ['fix', 'replace', 'update']):
                action_type = 'fix'
            elif any(word in pattern.lower() for word in ['add', 'include']):
                action_type = 'add'
            break
    
    if not action_text and not suggestions:
        # Fallback: extract first meaningful sentence
        lines = [line.strip() for line in body.split('\n') if line.strip()]
        for line in lines:
            if (len(line) > 20 and 
                not line.startswith(('>', '#', '-', '*', '```', '<details>')) and
                '**' not in line[:10]):  # Skip markdown headers
                action_text = line[:120]
                break
    
    if action_text or suggestions:
        return {
            'action': action_text or 'See suggestion',
            'type': action_type,
            'suggestions': [s.strip() for s in suggestions[:1]]  # Only first suggestion
        }
    
    return None


def process_coderabbit_data(data: Dict) -> List[Dict]:
    """Process CodeRabbit comments and reviews into actionable items."""
    actionable_items = []
    
    # Process review comments (file-specific)
    for comment in data['comments']:
        if not is_coderabbit_comment(comment):
            continue
            
        content = extract_actionable_content(comment.get('body', ''))
        if content:
            actionable_items.append({
                'file': comment.get('path', 'unknown'),
                'line': comment.get('line') or comment.get('original_line'),
                'content': content,
                'url': comment.get('html_url', '')
            })
    
    # Process general reviews
    for review in data['reviews']:
        if not is_coderabbit_comment(review):
            continue
            
        content = extract_actionable_content(review.get('body', ''))
        if content:
            actionable_items.append({
                'file': 'general',
                'line': None,
                'content': content,
                'url': review.get('html_url', '')
            })
    
    return actionable_items


def format_for_ai(items: List[Dict], pr_number: int) -> Dict:
    """Format actionable items for AI consumption."""
    prompts = []
    
    for i, item in enumerate(items, 1):
        file_location = item['file']
        if item['line']:
            file_location += f" at line {item['line']}"
        
        prompt = f"Fix #{i} in {file_location}: {item['content']['action']}"
        
        if item['content']['suggestions']:
            prompt += f"\n\nSuggested change:\n```\n{item['content']['suggestions'][0]}\n```"
        
        prompts.append({
            'id': i,
            'prompt': prompt,
            'file': item['file'],
            'line': item['line'],
            'type': item['content']['type'],
            'url': item['url']
        })
    
    return {
        'pr_number': pr_number,
        'total_fixes': len(prompts),
        'prompts': [p['prompt'] for p in prompts],
        'detailed_prompts': prompts,
        'post_fix_commands': [
            'make lint',
            'make test',
            'make format'
        ],
        'summary': f"Found {len(prompts)} actionable CodeRabbit suggestions for PR #{pr_number}"
    }


def execute_post_fix_commands(commands: List[str], args) -> None:
    """Execute the post-fix commands and report their status."""
    for cmd in commands:
        try:
            if not args.quiet:
                print(f"🔄 Running {cmd}...", file=sys.stderr)
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                if not args.quiet:
                    print(f"✅ {cmd} completed successfully", file=sys.stderr)
            else:
                print(f"❌ {cmd} failed with error:", file=sys.stderr)
                print(result.stderr, file=sys.stderr)
        except Exception as e:
            print(f"❌ Error running {cmd}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Fast CodeRabbit AI formatter - GitHub API to AI prompts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process current repo PR 149
  %(prog)s 149
  
  # Process specific repo
  %(prog)s 149 --repo owner/repo
  
  # Output to file
  %(prog)s 149 --output fixes.json
  
  # Quiet mode (JSON only)
  %(prog)s 149 --quiet
        """
    )
    
    parser.add_argument('pr_number', type=int, help='Pull request number')
    parser.add_argument('--repo', help='Repository (owner/repo) - auto-detected if not provided')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Only output JSON, no progress messages')
    
    args = parser.parse_args()
    
    # Get repository info
    repo_name = args.repo or get_repo_info()
    
    if not args.quiet:
        print(f"🔍 Fetching CodeRabbit comments for {repo_name} PR #{args.pr_number}...", file=sys.stderr)
    
    try:
        # Fetch PR data
        pr_data = fetch_pr_data(args.pr_number, repo_name)
        
        if not args.quiet:
            comment_count = len([c for c in pr_data['comments'] if is_coderabbit_comment(c)])
            review_count = len([r for r in pr_data['reviews'] if is_coderabbit_comment(r)])
            print(f"📝 Found {comment_count} CodeRabbit comments, {review_count} reviews", file=sys.stderr)
        
        # Process into actionable items
        actionable_items = process_coderabbit_data(pr_data)
        
        # Format for AI
        result = format_for_ai(actionable_items, args.pr_number)
        
        if not args.quiet:
            print(f"✅ Generated {result['total_fixes']} actionable prompts", file=sys.stderr)
        
        # Output
        output_json = json.dumps(result, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_json)
            if not args.quiet:
                print(f"💾 Saved to {args.output}", file=sys.stderr)
        else:
            print(output_json)
        
        # Execute post-fix commands
        if not args.quiet:
            print("\n🔧 Running post-fix commands...", file=sys.stderr)
        execute_post_fix_commands(result['post_fix_commands'], args)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ GitHub API error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()