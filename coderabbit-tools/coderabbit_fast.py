#!/usr/bin/env python3
"""
Fast CodeRabbit Tool - Optimized for AI formatting only
Since automation doesn't work, this focuses purely on generating useful AI prompts.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path


def find_script(script_name: str) -> str:
    """Find a script in the same directory."""
    script_dir = Path(__file__).parent
    script_path = script_dir / script_name
    if script_path.exists():
        return str(script_path)
    raise FileNotFoundError(f"Script {script_name} not found in {script_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Fast CodeRabbit AI formatter (optimized)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate AI prompts for PR 149
  %(prog)s 149
  
  # Specific repository  
  %(prog)s 149 --repo owner/repo
  
  # Save output to file
  %(prog)s 149 --output coderabbit_fixes.json
  
  # Quiet mode (only JSON output)
  %(prog)s 149 --quiet

This optimized version:
- Uses parallel GitHub API calls for speed
- Focuses only on actionable CodeRabbit suggestions  
- Includes post-fix commands (make lint, make test, make format)
- Skips the automation pipeline (since it doesn't work reliably)
        """
    )
    
    parser.add_argument('pr_number', type=int, help='Pull request number')
    parser.add_argument('--repo', help='Repository name (owner/repo)')
    parser.add_argument('--output', '-o', help='Output file for results')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode - only JSON output')
    
    args = parser.parse_args()
    
    try:
        # Find the optimized AI formatter
        ai_script = find_script('coderabbit_ai_only.py')
        
        # Build command
        cmd = ['python3', ai_script, str(args.pr_number)]
        
        if args.repo:
            cmd.extend(['--repo', args.repo])
        
        if args.output:
            cmd.extend(['--output', args.output])
            
        if args.quiet:
            cmd.append('--quiet')
        
        # Execute
        result = subprocess.run(cmd, check=True)
        
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == '__main__':
    main()