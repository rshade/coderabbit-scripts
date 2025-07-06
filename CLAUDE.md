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
- Use relative paths for portability (e.g., `coderabbit-tools/script.py`)

## Enhanced AI Formatter and Prompts

### CodeRabbit AI Formatter Improvements (2024-12)
The `coderabbit_ai_formatter.py` was significantly enhanced to address issues where Claude Code would:
- Create more problems than it solved (100+ new CodeRabbit comments)
- Only partially complete fixes
- Create files without EOF newlines causing lint failures
- Generate markdown files that fail markdownlint

**Key Enhancements Made:**
- **Psychological conditioning**: Replaced weak "should" language with mandatory "MUST/NEVER" 
- **Sequential processing lockdown**: Force one-issue-at-a-time with TodoWrite tracking
- **Bulletproof validation**: Mandatory validation after EVERY edit
- **File creation standards**: EOF newlines, markdownlint compliance built-in
- **Error recovery procedures**: Specific rollback and retry protocols

### Optimized User Prompts
Created two systematic prompts that leverage the enhanced formatter:

**CodeRabbitPrompt.md**: For fixing existing CodeRabbit issues
- 4-phase structured approach (Analysis → Sequential Resolution → Coverage → Validation)
- Leverages enhanced AI formatter's built-in safeguards
- Includes specific codecov improvement strategies

**Github_Development_Prompt.md**: For implementing new GitHub issues  
- 5-phase approach with mandatory verification checkpoint
- TodoWrite integration for comprehensive planning
- Complete testing and documentation requirements

### Critical Success Patterns Discovered
1. **TodoWrite/TodoRead tools are essential** - Manual tracking leads to incomplete work
2. **Sequential processing prevents cascade failures** - Never work on multiple issues simultaneously
3. **Validation after every change** - Batching validation leads to hard-to-debug failures
4. **Verification checkpoints** - Human approval before coding prevents misinterpretation
5. **File creation standards** - EOF newlines and markdownlint compliance must be explicit
6. **Psychological conditioning works** - Strong mandatory language prevents premature completion

### Validation Commands
Always run these commands after any changes:
```bash
make lint && coderabbit-linter && make validate && make test
```

### New Tools Added
- `coderabbit-linter`: Pre-commit linting wrapper for `coderabbit_linter.py`