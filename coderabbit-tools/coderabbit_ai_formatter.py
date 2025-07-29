#!/usr/bin/env python3
"""
Parse CodeRabbit comments from GitHub PR into AI-friendly format
"""
import json
import subprocess
import sys
import re
import os

def get_language_from_filename(filename):
    """Get language from filename extension"""
    extension_map = {
        'py': 'python',
        'js': 'javascript',
        'ts': 'typescript',
        'go': 'go',
        'java': 'java',
        'rb': 'ruby',
        'php': 'php',
        'cs': 'csharp',
        'cpp': 'cpp',
        'c': 'c',
        'h': 'c',
        'hpp': 'cpp',
        'sh': 'bash',
        'html': 'html',
        'css': 'css',
        'scss': 'scss',
        'less': 'less',
        'json': 'json',
        'yaml': 'yaml',
        'yml': 'yaml',
        'md': 'markdown',
        'sql': 'sql',
        'kt': 'kotlin',
        'kts': 'kotlin',
        'swift': 'swift',
        'rs': 'rust',
    }
    extension = filename.split('.')[-1]
    return extension_map.get(extension, '')


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

def extract_detailed_instruction(body):
    """Extract detailed instructions from CodeRabbit comments, including AI Agents prompts"""
    
    # First, look for "Prompt for AI Agents" section specifically
    ai_prompt_pattern = r'<summary>🤖 Prompt for AI Agents</summary>\s*```(.*?)```'
    ai_prompt_match = re.search(ai_prompt_pattern, body, re.DOTALL)
    if ai_prompt_match:
        return ai_prompt_match.group(1).strip()
    
    # Look for collapsible details sections that might contain detailed instructions
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
            if len(instruction) > 50:  # Only use if it's substantial
                return instruction
    
    return None

def extract_review_body_issues(body, reviewer_type="coderabbit"):
    """Extract actionable issues from review body text"""
    issues = []
    
    # For CodeRabbit, we should NOT extract anything from review bodies
    # because they contain way too much noise and context.
    # The real actionable issues are in individual line comments, not review summaries.
    
    if reviewer_type == "coderabbit":
        # Extract duplicate comments from CodeRabbit review body
        # Look for the duplicate comments section which contains actionable issues
        # Handle nested blockquotes by finding the start and end manually
        start_pattern = r'<summary>♻️ Duplicate comments \(\d+\)</summary><blockquote>'
        start_match = re.search(start_pattern, body)
        
        if start_match:
            # Find the end of the duplicate section
            start_pos = start_match.end()
            # Look for the closing </blockquote></details> that belongs to this section
            remaining = body[start_pos:]
            
            # Count nested blockquotes to find the correct closing
            blockquote_count = 1
            pos = 0
            while pos < len(remaining) and blockquote_count > 0:
                open_match = re.search(r'<blockquote>', remaining[pos:])
                close_match = re.search(r'</blockquote>', remaining[pos:])
                
                if open_match and close_match:
                    if open_match.start() < close_match.start():
                        blockquote_count += 1
                        pos += open_match.end()
                    else:
                        blockquote_count -= 1
                        pos += close_match.end()
                elif close_match:
                    blockquote_count -= 1
                    pos += close_match.end()
                else:
                    break
            
            if blockquote_count == 0:
                duplicate_content = remaining[:pos - len('</blockquote>')]
                duplicate_match = True
            else:
                duplicate_match = False
        else:
            duplicate_match = False
        
        if duplicate_match:
            # Parse individual files within the blockquote
            file_pattern = r'<details>\s*<summary>([^<]+?)\s*\((\d+)\)</summary><blockquote>(.*?)</blockquote></details>'
            file_matches = re.finditer(file_pattern, duplicate_content, re.DOTALL)
            
            for file_match in file_matches:
                file_path = file_match.group(1).strip()
                issue_content = file_match.group(3)
                
                # Split by '---' to get individual issues
                individual_issues = issue_content.split('\n---\n')
                
                for individual_issue in individual_issues:
                    individual_issue = individual_issue.strip()
                    if not individual_issue:
                        continue
                    
                    # Look for line patterns like: `123-125`: **Description**
                    issue_pattern = r'`(\d+(?:-\d+)?)`: \*\*([^*]+)\*\*(.*?)(?=```|$)'
                    issue_match = re.search(issue_pattern, individual_issue, re.DOTALL)
                    
                    if issue_match:
                        line_range = issue_match.group(1)
                        title = issue_match.group(2).strip()
                        description = issue_match.group(3).strip()
                        
                        # Parse line number
                        if '-' in line_range:
                            start_line = int(line_range.split('-')[0])
                        else:
                            start_line = int(line_range)
                        
                        issues.append({
                            'file': file_path,
                            'line': start_line,
                            'title': title,
                            'description': description,
                            'code_suggestions': [],
                            'source': 'duplicate_comment'
                        })
                    else:
                        # Try to match general issues without line numbers
                        general_pattern = r'\*\*([^*]+)\*\*(.*?)(?=```|$)'
                        general_match = re.search(general_pattern, individual_issue, re.DOTALL)
                        
                        if general_match:
                            title = general_match.group(1).strip()
                            description = general_match.group(2).strip()
                            
                            issues.append({
                                'file': file_path,
                                'line': None,
                                'title': title,
                                'description': description,
                                'code_suggestions': [],
                                'source': 'duplicate_comment'
                            })
        
        return issues
    
    elif reviewer_type == "copilot":
        # Copilot patterns - look for file references and suggestions
        patterns = [
            # Pattern: **file.go:line** Description
            r'\*\*([^*]+\.go):(\d+)\*\*\s*(.*?)(?=\n\*\*|\n```|\n\n|$)',
            # Pattern: file mentions with suggestions
            r'([a-zA-Z0-9_/-]+\.go)\s*(?:line?\s*(\d+))?\s*[:\-]\s*(.*?)(?=```suggestion|```go|\n\n|$)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, body, re.DOTALL | re.IGNORECASE)
            for match in matches:
                file_path = match.group(1)
                line_num = match.group(2) if match.group(2) else None
                description = match.group(3).strip()
                
                # Extract suggestions
                suggestion_pattern = r'```suggestion\s*(.*?)```'
                suggestions = re.findall(suggestion_pattern, body[match.end():], re.DOTALL)
                
                issues.append({
                    'file': file_path,
                    'line': line_num,
                    'title': f"Copilot suggestion for {file_path}",
                    'description': description,
                    'code_suggestions': suggestions,
                    'source': 'review_body'
                })
    
    return issues

def classify_priority(body, path, action):
    """Classify issue priority based on content"""
    high_priority_keywords = [
        'security', 'vulnerability', 'injection', 'xss', 'authentication', 'authorization',
        'memory leak', 'resource leak', 'deadlock', 'race condition', 'null pointer',
        'error handling', 'exception', 'crash', 'fail', 'critical'
    ]
    
    medium_priority_keywords = [
        'performance', 'optimization', 'efficiency', 'timeout', 'connection',
        'database', 'query', 'test', 'coverage', 'validation', 'input'
    ]
    
    low_priority_keywords = [
        'formatting', 'whitespace', 'comment', 'documentation', 'typo',
        'naming', 'style', 'convention', 'trailing', 'spaces'
    ]
    
    body_lower = body.lower()
    action_lower = action.lower() if action else ''
    
    # Check file patterns for priority
    if any(pattern in path.lower() for pattern in ['auth', 'security', 'jwt', 'password']):
        return 'high'
    
    if any(pattern in path.lower() for pattern in ['test', 'spec', 'mock']):
        return 'medium'
    
    # Check content patterns
    for keyword in high_priority_keywords:
        if keyword in body_lower or keyword in action_lower:
            return 'high'
    
    for keyword in medium_priority_keywords:
        if keyword in body_lower or keyword in action_lower:
            return 'medium'
    
    for keyword in low_priority_keywords:
        if keyword in body_lower or keyword in action_lower:
            return 'low'
    
    return 'medium'  # Default

def is_resolved_or_outdated(comment):
    """Check if a comment is resolved or outdated"""
    body = comment.get('body', '')
    
    # For CodeRabbit, only process comments with specific actionable markers
    # This is the key insight: only comments with these emoji markers are actually actionable
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
    
    # If this is a CodeRabbit comment but doesn't have actionable markers, skip it
    # EXCEPTION: Don't skip if this is a review body (might contain duplicate comments)
    if 'coderabbitai' in comment.get('user', {}).get('login', '').lower():
        # Check if this is a review body (has duplicate comments section)
        if '♻️ Duplicate comments' in body:
            return False  # Don't skip review bodies with duplicate comments
        
        has_actionable_marker = any(marker in body for marker in actionable_markers)
        if not has_actionable_marker:
            return True  # Skip comments without actionable markers
    
    # Check for explicit resolved indicators - be more specific
    # Look for patterns that indicate the issue is actually resolved
    body_lower = body.lower()
    resolved_patterns = [
        r'\b(resolved|fixed|done|completed)\b',  # Standalone words
        r'✅.*resolved',  # Checkmark with resolved
        r'✅ addressed in commit',  # CodeRabbit's addressed marker
        r'✅ Addressed in commit',  # Case-sensitive variant
        r'this has been (resolved|fixed|addressed)',
        r'issue (resolved|fixed)',
        r'(no longer|not) (applicable|relevant)',
        r'outdated.*resolved'
    ]
    
    # Check for explicit resolved indicators using regex patterns
    import re
    for pattern in resolved_patterns:
        if re.search(pattern, body_lower):
            return True
    
    # Check if comment is in a resolved conversation
    # GitHub API includes resolved status
    if comment.get('in_reply_to_id') and comment.get('resolved', False):
        return True
        
    return False

def parse_coderabbit_comment(comment):
    """Parse a CodeRabbit comment into AI-friendly format"""
    body = comment.get('body', '')
    
    # Skip non-CodeRabbit comments
    if 'coderabbitai' not in comment.get('user', {}).get('login', '').lower():
        return None
    
    # Skip resolved or outdated comments
    if is_resolved_or_outdated(comment):
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
    
    # Try to extract detailed instruction first
    detailed_instruction = extract_detailed_instruction(body)
    
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
        # Look for more detailed patterns
        (r'In\s+[^,]+around lines?\s+\d+(?:\s+to\s+\d+)?,\s+(.*?)(?:\.|Replace|Consider|This)', 'detailed_fix'),
    ]
    
    action = None
    action_type = 'general'
    
    # Use detailed instruction if available
    if detailed_instruction:
        action = detailed_instruction
        action_type = 'detailed_fix'
    else:
        for pattern, fix_type in action_patterns:
            match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
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
            if line and not line.startswith(('>', '#', '-', '*', '```', '<')):
                action = line[:200]
                break
    
    if not action:
        return None
    
    # Classify priority
    priority = classify_priority(body, path, action)
    
    return {
        'file': path,
        'line': line,
        'action': action,
        'type': action_type,
        'priority': priority,
        'suggestions': suggestions,
        'detailed_instruction': detailed_instruction,
        'full_comment': body[:1000] + '...' if len(body) > 1000 else body  # Increased limit
    }

def format_ai_prompts(parsed_comments, prioritize=False, gemini_format=False):
    """Format parsed comments into AI prompts"""
    prompts = []
    
    # Sort by priority if requested
    if prioritize:
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        parsed_comments = sorted(parsed_comments, key=lambda x: priority_order.get(x.get('priority', 'medium'), 1))
    
    gemini_template = """TASK #<TASK_NUMBER>: <FILE_PATH_AND_LINE>

ISSUE: <ISSUE_DESCRIPTION>

SUGGESTED FIX:
```<LANGUAGE>
<SUGGESTED_CODE>
```

✅ MANDATORY EXECUTION STEPS:
1. Inform the user you are starting this task.
2. Read the entire file `<FILE_PATH>` to understand its full context.
3. Make ONLY the minimal change required to fix this issue, as described above.
4. Run the full validation suite: `make lint && make validate && make test`.
5. If validation fails, revert the change, analyze the error, and try a different approach.
6. Once validation passes, inform the user that the task is complete.

DO NOT:
- Make any changes not directly related to this specific issue.
- Add, remove, or modify imports, dependencies, or variables unless explicitly required.
- Change any function signatures or data structures.
- Add comments, documentation, or perform unrelated formatting changes.
- Proceed to the next task if validation for the current one fails.

SUCCESS CRITERIA:
- The issue is fixed exactly as described.
- All validation commands pass: `make lint && make validate && make test`.
- No new issues are introduced in the codebase.
- No unrelated files or code have been modified.
"""

    # Add instructions to avoid creating new CodeRabbit issues
    instructions = """MANDATORY EXECUTION PROTOCOL - FAILURE TO FOLLOW RESULTS IN 100+ NEW CODERABBIT ISSUES

WARNING: Previous attempts at fixing these issues created cascading failures, breaking builds, and generating dozens of new CodeRabbit comments. You MUST follow this protocol EXACTLY or you will create more problems than you solve.

MANDATORY PRE-WORK REQUIREMENTS:
1. You MUST use TodoWrite tool to create individual todos for EVERY issue listed below before making any changes
2. You MUST verify make lint, make validate, make test commands exist and work before starting
3. You MUST read the full context of any file before editing it
4. NEVER proceed until these requirements are met

SEQUENTIAL EXECUTION LOCKDOWN:
- You MUST work on ONE issue at a time, NEVER multiple simultaneously  
- You MUST mark each todo as "in_progress" before working on it
- You MUST run full validation (make lint, make validate, make test) after EVERY single edit
- You MUST fix any validation failures immediately before proceeding
- You MUST mark todo as "completed" only after validation passes
- NEVER move to the next issue until current one is 100% complete with passing validation

ABSOLUTELY PROHIBITED ACTIONS (Violation creates cascading failures):
- Making any "improvements" not explicitly requested in the issue
- Changing multiple files for one issue unless explicitly required
- Adding new imports, dependencies, or variables unless explicitly required
- Modifying function signatures unless explicitly required
- Adding comments, documentation, or formatting changes unless explicitly required
- Batching multiple edits before validation
- Proceeding when validation fails
- Claiming completion without running final validation
- Creating files without proper EOF newlines (causes lint failures)
- Creating markdown files that don't pass markdownlint (causes build failures)

MANDATORY COMPLETION CRITERIA:
Before claiming ANY work is complete, you MUST:
1. Use TodoRead tool to verify ALL todos are marked "completed"
2. Run make lint, make validate, make test and confirm ALL pass
3. Confirm no new files were created unless explicitly required
4. Confirm no unrelated code was modified
5. NEVER say "done" or "completed" until ALL criteria are met

VALIDATION PROTOCOL (MANDATORY after every edit):
1. Run: make lint (fix any new issues immediately)
2. Run: make validate (fix any new issues immediately) 
3. Run: make test (fix any new issues immediately)
4. If ANY command fails, you MUST revert the change and try a different approach
5. NEVER proceed to next issue until ALL validation passes

ERROR RECOVERY PROTOCOL:
If validation fails after your edit:
1. IMMEDIATELY revert the exact change you made
2. Re-read the original issue and file context
3. Try a more minimal approach
4. If still failing, ask for clarification rather than guessing
5. NEVER leave the codebase in a broken state

CHANGE MINIMIZATION RULES:
- Read the entire file before making any edits to understand context
- Use exact string matching for all edits - preserve whitespace, indentation, line endings
- Make ONLY the specific change requested, nothing more
- If the issue is unclear, ask for clarification rather than assuming
- Test your change in isolation before moving on

MANDATORY FILE CREATION STANDARDS (CRITICAL - prevents lint failures):
When creating ANY new file, you MUST:
1. ALWAYS end files with a single newline character (EOF newline) - missing this causes lint failures
2. For Markdown files (.md), ensure they pass markdownlint by following these rules:
   - Use proper heading hierarchy (# then ## then ### - no skipping levels)
   - Add blank lines before and after headings
   - Use consistent list markers (- for unordered, 1. for ordered)
   - Wrap long lines at 80-100 characters
   - End file with single newline
   - No trailing whitespace on any line
3. For all code files:
   - Follow existing project indentation (tabs vs spaces)
   - Maintain consistent line endings (LF vs CRLF)
   - Include proper file encoding (UTF-8 unless project specifies otherwise)
   - End with single newline character
4. ALWAYS run relevant linters on newly created files:
   - markdownlint for .md files
   - Project-specific linters for code files
   - Fix ALL linting errors before marking task complete

CONSEQUENCES OF RULE VIOLATIONS:
- Creating new lint errors = 10+ new CodeRabbit comments
- Breaking tests = 20+ new CodeRabbit comments  
- Making unrequested changes = 30+ new CodeRabbit comments
- Not following sequential process = Incomplete fixes and another full review cycle
- Each violation wastes hours of developer time and delays merging

SUCCESS METRICS:
- ALL issues in todo list marked completed
- ALL validation commands pass
- ZERO new CodeRabbit issues created
- ZERO unrelated code modified
- Build remains stable and tests pass

REMEMBER: The goal is to fix ALL issues perfectly in ONE attempt. Creating even one new issue means the entire process failed."""
    
    for i, comment in enumerate(parsed_comments, 1):
        if not comment:
            continue

        if gemini_format:
            file_location = f"{comment['file']}"
            if comment.get('line'):
                file_location += f":{comment['line']}"

            task_description = comment.get('detailed_instruction') or comment['action']

            prompt = gemini_template.replace('<TASK_NUMBER>', str(i))
            prompt = prompt.replace('<FILE_PATH_AND_LINE>', file_location)
            prompt = prompt.replace('<ISSUE_DESCRIPTION>', task_description)
            prompt = prompt.replace('<FILE_PATH>', comment['file'])

            if comment.get('suggestions'):
                language = get_language_from_filename(comment['file'])
                prompt = prompt.replace('<LANGUAGE>', language)
                prompt = prompt.replace('<SUGGESTED_CODE>', comment['suggestions'][0])
            else:
                # Remove the SUGGESTED FIX section if no suggestions
                prompt = re.sub(r'SUGGESTED FIX:\n```<LANGUAGE>\n<SUGGESTED_CODE>\n```\n', '', prompt)
            
            
            
            

        else:
            # Build comprehensive task prompt
            file_location = f"{comment['file']}"
            if comment.get('line'):
                file_location += f":line {comment['line']}"
                
            # Use detailed instruction if available, otherwise use action
            task_description = comment.get('detailed_instruction') or comment['action']
            
            prompt = """TASK #{i}: {file_location}

ISSUE: {task_description}""".format(i=i, file_location=file_location, task_description=task_description)

            # Add suggestions if available
            if comment.get('suggestions'):
                prompt += """

SUGGESTED FIX:
```
{suggestion}
```""".format(suggestion=comment['suggestions'][0])

            # Add mandatory execution steps
            prompt += """

MANDATORY EXECUTION STEPS:
1. Use TodoWrite to add this task to your todo list
2. Mark this task as "in_progress" before starting
3. Read the entire file {file} to understand context
4. Make ONLY the minimal change required to fix this issue
5. If creating new files, ENSURE they have proper EOF newlines and pass linting
6. Run validation: make lint && make validate && make test
7. Fix any validation failures immediately
8. Mark task as "completed" only after all validation passes
9. NEVER proceed to next task until this one is 100% complete

DO NOT:
- Make any changes not directly related to this issue
- Add imports, comments, or formatting unless explicitly required
- Modify other files unless explicitly required for this fix
- Create files without EOF newlines (causes lint failures)
- Create markdown files that fail markdownlint
- Proceed if validation fails

SUCCESS CRITERIA:
- Issue is fixed exactly as described
- All validation commands pass: make lint && make validate && make test
- Any new files created have proper formatting and pass linting
- No new issues introduced
- Todo marked as "completed""".format(file=comment['file'])

        # Add the global instructions to the first prompt only
        if i == 1:
            prompt = instructions + "\n\n" + prompt
            if not gemini_format:
                # Add pre-flight checks to first task only for non-Gemini format
                prompt += """

MANDATORY PRE-FLIGHT CHECKS (Run these BEFORE starting any work):
1. Verify make lint command exists and works
2. Verify make validate command exists and works  
3. Verify make test command exists and works
4. Use TodoWrite to create todos for ALL tasks in this list
5. NEVER start actual fixes until all pre-flight checks pass"""

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

def main(pr_number, repo_name=None, prioritize=False, gemini_format=False):
    print(f"Fetching CodeRabbit and Copilot comments for PR #{pr_number}...")
    
    # Get all PR comments and reviews
    comments = get_pr_comments(pr_number, repo_name)
    reviews = get_pr_reviews(pr_number, repo_name)
    
    # Parse individual line comments (existing functionality)
    parsed = []
    
    for comment in comments:
        parsed_comment = parse_coderabbit_comment(comment)
        if parsed_comment:
            parsed.append(parsed_comment)
    
    # Parse review body comments (NEW - this is what was missing!)
    current_file_context = None
    for review in reviews:
        user_login = review.get('user', {}).get('login', '').lower()
        body = review.get('body', '')
        
        if 'coderabbitai' in user_login:
            # Skip if review is resolved/outdated
            if is_resolved_or_outdated(review):
                continue
                
            # Extract issues from CodeRabbit review body
            review_issues = extract_review_body_issues(body, "coderabbit")
            for issue in review_issues:
                # Convert to our standard format
                parsed_comment = {
                    'file': issue['file'],
                    'line': issue['line'],
                    'action': f"{issue['title']} {issue['description']}",
                    'type': 'review_body_fix',
                    'priority': classify_priority(issue['description'], issue['file'], issue['title']),
                    'suggestions': issue['code_suggestions'],
                    'detailed_instruction': f"In {issue['file']} around lines {issue['line']}, {issue['description']}",
                    'full_comment': f"{issue['title']}: {issue['description']}"
                }
                parsed.append(parsed_comment)
                
        elif 'copilot' in user_login:
            # Skip if review is resolved/outdated
            if is_resolved_or_outdated(review):
                continue
                
            # Extract issues from Copilot review body
            review_issues = extract_review_body_issues(body, "copilot")
            for issue in review_issues:
                parsed_comment = {
                    'file': issue['file'],
                    'line': issue['line'],
                    'action': f"{issue['title']} {issue['description']}",
                    'type': 'copilot_suggestion',
                    'priority': classify_priority(issue['description'], issue['file'], issue['title']),
                    'suggestions': issue['code_suggestions'],
                    'detailed_instruction': f"In {issue['file']} around line {issue['line']}, {issue['description']}",
                    'full_comment': f"{issue['title']}: {issue['description']}"
                }
                parsed.append(parsed_comment)
        
        # Also check old review comment processing (for compatibility)
        if 'coderabbitai' in user_login and not is_resolved_or_outdated(review):
            parsed_comment = parse_coderabbit_comment({'body': body, 'path': 'general', 'user': review.get('user')})
            if parsed_comment:
                parsed.append(parsed_comment)
    
    # Remove duplicates based on file, line, and action similarity
    unique_parsed = []
    seen = set()
    for comment in parsed:
        key = (comment['file'], comment.get('line'), comment['action'][:100])  # First 100 chars of action
        if key not in seen:
            seen.add(key)
            unique_parsed.append(comment)
    
    print(f"Found {len(comments)} line comments, {len(reviews)} reviews, extracted {len(parsed)} total issues, {len(unique_parsed)} unique unresolved issues")
    
    # Format into AI prompts
    ai_prompts = format_ai_prompts(unique_parsed, prioritize, gemini_format)
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
        print("Usage: coderabbit_ai_formatter.py <pr_number> [repo_name] [--prioritize] [--gemini]")
        sys.exit(1)
    
    pr_number = int(sys.argv[1])
    repo_name = None
    prioritize = False
    gemini_format = False
    
    for arg in sys.argv[2:]:
        if arg == '--prioritize':
            prioritize = True
        elif arg == '--gemini':
            gemini_format = True
        else:
            repo_name = arg
    
    main(pr_number, repo_name, prioritize, gemini_format)