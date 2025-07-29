#!/usr/bin/env python3
"""
CodeRabbit Pipeline - Complete workflow for fetching, parsing, and applying CodeRabbit fixes.
Chains together fetch_github_comments.py, parse_coderabbit_comments_v2.py, and apply_coderabbit_fixes_v2.py
"""

import argparse
import subprocess
import sys
import os
import tempfile
import json
from typing import List, Optional


def run_command(cmd: List[str], description: str, input_data: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"🔄 {description}...")
    
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            text=True,
            capture_output=True,
            check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error in {description}:", file=sys.stderr)
        print(f"Command: {' '.join(cmd)}", file=sys.stderr)
        print(f"Exit code: {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(f"Stdout: {e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"Stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def find_script(script_name: str) -> str:
    """Find a script in the same directory as this script or in PATH."""
    # Check same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(script_dir, script_name)
    if os.path.exists(local_path):
        return local_path
    
    # Check in PATH
    import shutil
    path_script = shutil.which(script_name)
    if path_script:
        return path_script
    
    # Not found
    raise FileNotFoundError(f"Script {script_name} not found in {script_dir} or PATH")


def main():
    parser = argparse.ArgumentParser(
        description='Complete CodeRabbit workflow: fetch, parse, and apply fixes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process PR 149 in current repo
  %(prog)s 149
  
  # Process specific repo and PR
  %(prog)s rshade/cronai 149
  
  # Dry run to see what would be changed
  %(prog)s 149 --dry-run
  
  # Only apply specific types of fixes
  %(prog)s 149 --filter-type format_fix
  
  # Save intermediate files for debugging
  %(prog)s 149 --keep-files --output-dir ./debug
  
  # Custom base path for applying fixes
  %(prog)s 149 --base-path /path/to/repo

This script chains together:
1. fetch_github_comments.py - Fetch all PR comments
2. parse_coderabbit_comments_v2.py - Parse CodeRabbit comments
3. apply_coderabbit_fixes_v2.py - Apply the fixes
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
        '--base-path',
        default='.',
        help='Base path for applying fixes (default: current directory)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making actual changes'
    )
    
    parser.add_argument(
        '--filter-type',
        choices=[
            'format_fix', 'input_validation', 'error_handling', 'test_fix', 'config_fix',
            'security_fix', 'performance_fix', 'import_fix',
            # CodeRabbit severity levels
            'potential_issue', 'refactor_suggestion', 'nitpick_assertive', 'verification',
            # Combined options
            'high_priority',    # potential_issue + security_fix + error_handling + input_validation
            'all_issues'        # everything including nitpicks
        ],
        help='Only apply fixes of this type'
    )
    
    parser.add_argument(
        '--keep-files',
        action='store_true',
        help='Keep intermediate files (comments.json, analysis.json)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='.',
        help='Directory for output files when --keep-files is used (default: current directory)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Only show summary, do not apply fixes'
    )
    
    parser.add_argument(
        '--ai-format',
        action='store_true',
        help='Use AI formatter to generate structured prompts instead of applying fixes'
    )
    
    parser.add_argument(
        '--gemini-format',
        action='store_true',
        help='Use Gemini formatter to generate structured prompts instead of applying fixes'
    )
    
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip pre-validation checks (make lint, validate, test)'
    )
    
    parser.add_argument(
        '--prioritize',
        action='store_true',
        help='Group issues by priority (high/medium/low) for systematic fixing'
    )
    
    parser.add_argument(
        '--include-nitpicks',
        action='store_true',
        help='Include nitpick (assertive) comments that are normally filtered out'
    )

    parser.add_argument(
        '--exclude-low-priority', 
        action='store_true',
        help='Exclude low-priority suggestions and nitpicks'
    )
    
    args = parser.parse_args()
    
    # Parse repo and PR arguments
    if args.pr_number is not None:
        # Format: repo pr_number
        repo_arg = args.repo_or_pr
        pr_arg = str(args.pr_number)
    else:
        # Format: pr_number (auto-detect repo)
        repo_arg = None
        pr_arg = args.repo_or_pr
    
    # Find scripts
    try:
        if args.ai_format or args.gemini_format:
            ai_format_script = find_script('coderabbit_ai_formatter.py')
        else:
            fetch_script = find_script('fetch_github_comments.py')
            parse_script = find_script('parse_coderabbit_comments_v2.py')
            apply_script = find_script('apply_coderabbit_fixes_v2.py')
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        print("Make sure all scripts are in the same directory or in your PATH", file=sys.stderr)
        sys.exit(1)
    
    # Prepare temp files or output files
    if args.keep_files:
        os.makedirs(args.output_dir, exist_ok=True)
        comments_file = os.path.join(args.output_dir, 'github_comments.json')
        analysis_file = os.path.join(args.output_dir, 'coderabbit_analysis.json')
        cleanup_files = False
    else:
        # Use temporary files
        comments_fd, comments_file = tempfile.mkstemp(suffix='_comments.json')
        analysis_fd, analysis_file = tempfile.mkstemp(suffix='_analysis.json')
        os.close(comments_fd)
        os.close(analysis_fd)
        cleanup_files = True
    
    # Pre-validation checks (unless skipped)
    if not args.skip_validation and not args.ai_format:
        print("🔍 Running pre-validation checks...")
        validation_commands = [
            (['make', 'lint'], "Linting"),
            (['make', 'validate'], "Validation"),
            (['make', 'test'], "Testing")
        ]
        
        for cmd, desc in validation_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    print(f"⚠️  {desc} failed. CodeRabbit fixes may address these issues.")
                    if args.verbose:
                        print(f"Error output: {result.stderr}")
                else:
                    print(f"✅ {desc} passed")
            except subprocess.TimeoutExpired:
                print(f"⚠️  {desc} timed out")
            except FileNotFoundError:
                print(f"⚠️  {desc} command not found (make {cmd[1]})")
    
    try:
        if args.ai_format or args.gemini_format:
            # Use AI formatter directly
            ai_cmd = ['python3', ai_format_script, pr_arg]
            if repo_arg:
                ai_cmd.append(repo_arg)
            if args.prioritize:
                ai_cmd.append('--prioritize')
            if args.gemini_format:
                ai_cmd.append('--gemini')
            
            ai_result = run_command(ai_cmd, "Generating AI-formatted prompts")
            print("✅ AI-formatted prompts generated")
            print(ai_result.stdout)
            return
        
        # Step 1: Fetch GitHub comments
        fetch_cmd = ['python3', fetch_script]
        if repo_arg:
            fetch_cmd.extend([repo_arg, pr_arg])
        else:
            fetch_cmd.append(pr_arg)
        fetch_cmd.extend(['--output', comments_file])
        
        run_command(fetch_cmd, "Fetching GitHub comments")
        print(f"✅ Comments saved to {comments_file}")
        
        # Step 2: Parse CodeRabbit comments
        parse_cmd = [
            'python3', parse_script,
            '--input', comments_file,
            '--output', analysis_file
        ]
        
        parse_result = run_command(parse_cmd, "Parsing CodeRabbit comments")
        print(f"✅ Analysis saved to {analysis_file}")
        
        # Print parse output (contains summary)
        if parse_result.stdout:
            print(parse_result.stdout)
        
        # Check if we found any comments to process
        try:
            with open(analysis_file, 'r') as f:
                analysis_data = json.load(f)
            
            comments_count = analysis_data.get('total_comments', 0)
            if comments_count == 0:
                print("ℹ️  No CodeRabbit comments with AI prompts found. Nothing to apply.")
                return
            
        except Exception as e:
            print(f"⚠️  Could not read analysis file: {e}", file=sys.stderr)
        
        # Step 3: Apply fixes (unless summary-only)
        if not args.summary_only:
            apply_cmd = [
                'python3', apply_script,
                '--input', analysis_file,
                '--base-path', args.base_path
            ]
            
            if args.dry_run:
                apply_cmd.append('--dry-run')
            
            if args.filter_type:
                apply_cmd.extend(['--filter-type', args.filter_type])
            
            if args.verbose:
                apply_cmd.append('--verbose')
            
            if args.include_nitpicks:
                apply_cmd.append('--include-nitpicks')
            
            if args.exclude_low_priority:
                apply_cmd.append('--exclude-low-priority')
            
            apply_result = run_command(apply_cmd, "Applying fixes")
            print(f"✅ Fixes applied")
            
            # Print apply output
            if apply_result.stdout:
                print(apply_result.stdout)
        
        if args.keep_files:
            print(f"\n📁 Files saved:")
            print(f"   Comments: {comments_file}")
            print(f"   Analysis: {analysis_file}")
        
    finally:
        # Cleanup temporary files if needed
        if cleanup_files:
            try:
                os.unlink(comments_file)
                os.unlink(analysis_file)
            except OSError:
                pass


if __name__ == '__main__':
    main()