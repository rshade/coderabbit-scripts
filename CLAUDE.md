# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based automation toolkit that processes CodeRabbit AI code review comments from GitHub PRs and automatically applies suggested fixes to codebases. The project consists of shell wrapper scripts and Python tools that work together in a pipeline architecture.

## Common Commands

### Running the Complete Pipeline
```bash
# Process all CodeRabbit comments from a PR and apply fixes
./coderabbit-fix OWNER/REPO PR_NUMBER
```

### Individual Tool Usage
```bash
# Fetch comments from a PR
./coderabbit-fetch OWNER/REPO PR_NUMBER

# Parse CodeRabbit comments from saved JSON
./coderabbit-parse comments.json

# Apply fixes from parsed output
./coderabbit-apply fixes.json
```

### Python Tools Direct Usage
```bash
# Run the complete pipeline with Python
python coderabbit-tools/coderabbit_pipeline.py OWNER/REPO PR_NUMBER

# Dry-run mode (preview changes without applying)
python coderabbit-tools/apply_coderabbit_fixes_v2.py fixes.json --dry-run
```

## Architecture

### Data Flow
1. **fetch_github_comments.py**: Uses GitHub CLI to fetch PR comments → outputs JSON
2. **parse_coderabbit_comments_v2.py**: Extracts CodeRabbit suggestions → outputs structured fixes JSON
3. **apply_coderabbit_fixes_v2.py**: Applies fixes to the codebase → modifies files

### Fix Categories
The parser categorizes fixes into types:
- `format_fix`: Code formatting issues
- `input_validation`: Input validation improvements
- `error_handling`: Error handling enhancements
- `test_fix`: Test-related fixes
- `config_fix`: Configuration improvements
- `import_fix`: Import statement corrections

### Key Implementation Details
- All tools use JSON for intermediate data storage
- GitHub CLI (`gh`) is required for authentication
- Tools can be chained via shell pipes or used individually
- Each Python script has comprehensive error handling and logging

## Development Guidelines

### Adding New Fix Types
When extending the parser to handle new fix types:
1. Add the new category to `parse_coderabbit_comments_v2.py`
2. Update the fix detection logic in the same file
3. Ensure `apply_coderabbit_fixes_v2.py` can handle the new type

### Testing Changes
Since there's no formal test suite, test changes by:
1. Using dry-run mode to preview changes
2. Testing on a sample PR with known CodeRabbit comments
3. Verifying JSON output at each pipeline stage

### Shell Script Conventions
- All wrapper scripts follow the pattern: `coderabbit-[action]`
- Scripts pass arguments directly to Python tools
- Use absolute paths when calling Python scripts from wrappers