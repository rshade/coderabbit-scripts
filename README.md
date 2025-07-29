# CodeRabbit Scripts

A set of Python utilities for automatically processing CodeRabbit review comments and applying suggested fixes across multiple repositories.

## Shell Script Commands

### Main Pipeline Commands

#### `coderabbit-fix`
Complete pipeline - fetches, parses, and applies CodeRabbit fixes from a GitHub PR.

```bash
# Fix current repo
coderabbit-fix 149

# Fix specific repo
coderabbit-fix rshade/cronai 149

# Dry run (preview changes)
coderabbit-fix 149 --dry-run

# Filter by fix type
coderabbit-fix 149 --filter-type format_fix

# Verbose output
coderabbit-fix 149 --verbose

# Keep intermediate files for debugging
coderabbit-fix 149 --keep-files --output-dir ./debug
```

### Individual Tool Commands

#### `coderabbit-fetch`
Fetches GitHub PR comments using the `gh` CLI.

```bash
# Fetch from current repo (auto-detect from git remote)
coderabbit-fetch 149

# Fetch from specific repo
coderabbit-fetch rshade/cronai 149

# Save to custom file
coderabbit-fetch 149 --output my_comments.json

# Just show summary
coderabbit-fetch 149 --format summary
```

#### `coderabbit-parse`
Parses CodeRabbit comments and extracts AI prompts and code suggestions.

```bash
# Parse from default input file
coderabbit-parse

# Parse from specific file
coderabbit-parse --input my_comments.json

# Parse from stdin (for chaining)
cat comments.json | coderabbit-parse --input -

# Just show summary
coderabbit-parse --summary-only
```

#### `coderabbit-apply`
Applies fixes based on CodeRabbit AI prompts and suggestions.

```bash
# Apply fixes from analysis file
coderabbit-apply

# Dry run to see what would change
coderabbit-apply --dry-run

# Apply only specific types of fixes
coderabbit-apply --filter-type format_fix

# Apply to specific directory
coderabbit-apply --base-path /path/to/repo

# Verbose output
coderabbit-apply --verbose
```

### Validation and Linting

#### `coderabbit-linter`
Pre-commit linting tool to catch common CodeRabbit issues.

```bash
# Run linter on current directory
coderabbit-linter

# Run with verbose output
coderabbit-linter --verbose

# Check specific files
coderabbit-linter file1.go file2.py
```

## Python Tools (Direct Usage)

### Core Tools

#### `fetch_github_comments.py`
Fetches all comments from a GitHub PR using the `gh` CLI.

**Features:**
- Fetches issue comments, review comments, and reviews
- Auto-detects repository from git remote
- Supports explicit repository specification
- Uses `gh` CLI for authentication (no token management needed)

**Usage:**
```bash
# Fetch from current repo (auto-detect from git remote)
python3 coderabbit-tools/fetch_github_comments.py 149

# Fetch from specific repo
python3 coderabbit-tools/fetch_github_comments.py rshade/cronai 149

# Save to custom file
python3 coderabbit-tools/fetch_github_comments.py 149 --output my_comments.json

# Just show summary
python3 coderabbit-tools/fetch_github_comments.py 149 --format summary
```

#### `parse_coderabbit_comments_v2.py`
Parses CodeRabbit comments and extracts AI prompts and code suggestions.

**Features:**
- Extracts "Prompt for AI Agents" sections
- Identifies file paths and line numbers from prompts
- Categorizes comments by type and file
- Groups suggestions for easy processing

**Usage:**
```bash
# Parse from default input file
python3 coderabbit-tools/parse_coderabbit_comments_v2.py

# Parse from specific file
python3 coderabbit-tools/parse_coderabbit_comments_v2.py --input my_comments.json

# Parse from stdin (for chaining)
cat comments.json | python3 coderabbit-tools/parse_coderabbit_comments_v2.py --input -

# Just show summary
python3 coderabbit-tools/parse_coderabbit_comments_v2.py --summary-only
```

#### `apply_coderabbit_fixes_v2.py`
Applies fixes based on CodeRabbit AI prompts and suggestions.

**Features:**
- Detects fix types automatically (format_fix, input_validation, etc.)
- Supports dry-run mode for safety
- Handles different types of code changes
- Provides detailed feedback on applied fixes

**Usage:**
```bash
# Apply fixes from analysis file
python3 coderabbit-tools/apply_coderabbit_fixes_v2.py

# Dry run to see what would change
python3 coderabbit-tools/apply_coderabbit_fixes_v2.py --dry-run

# Apply only specific types of fixes
python3 coderabbit-tools/apply_coderabbit_fixes_v2.py --filter-type format_fix

# Apply to specific directory
python3 coderabbit-tools/apply_coderabbit_fixes_v2.py --base-path /path/to/repo

# Verbose output
python3 coderabbit-tools/apply_coderabbit_fixes_v2.py --verbose
```

#### `coderabbit_pipeline.py`
Complete workflow that chains all tools together.

**Features:**
- End-to-end processing from PR number to applied fixes
- Supports all options from individual tools
- Can save intermediate files for debugging
- Handles errors gracefully

**Usage:**
```bash
# Process PR 149 in current repo
python3 coderabbit-tools/coderabbit_pipeline.py 149

# Process specific repo and PR
python3 coderabbit-tools/coderabbit_pipeline.py rshade/cronai 149

# Dry run to see what would change
python3 coderabbit-tools/coderabbit_pipeline.py 149 --dry-run

# Only apply specific fix types
python3 coderabbit-tools/coderabbit_pipeline.py 149 --filter-type format_fix

# Keep intermediate files for debugging
python3 coderabbit-tools/coderabbit_pipeline.py 149 --keep-files --output-dir ./debug

# Verbose output
python3 coderabbit-tools/coderabbit_pipeline.py 149 --verbose
```

### Specialized Tools

#### `coderabbit_fast.py`
Fast processing mode for quick fixes.

#### `coderabbit_ai_only.py`
AI-only processing without applying fixes.

#### `coderabbit_ai_formatter.py`
Enhanced AI formatter for CodeRabbit fixes.

#### `coderabbit_linter.py`
Linting validation tool.

#### `validate_linters.py`
Linter validation utilities.

## Chaining Tools

You can chain the tools together manually for more control:

```bash
# Using shell commands
coderabbit-fetch 149 | coderabbit-parse --input - | coderabbit-apply --input - --dry-run

# Or save intermediate files
coderabbit-fetch 149 --output comments.json
coderabbit-parse --input comments.json --output analysis.json
coderabbit-apply --input analysis.json --dry-run

# Using Python tools directly
python3 coderabbit-tools/fetch_github_comments.py 149 | \
python3 coderabbit-tools/parse_coderabbit_comments_v2.py --input - | \
python3 coderabbit-tools/apply_coderabbit_fixes_v2.py --input - --dry-run

# Or save intermediate files
python3 coderabbit-tools/fetch_github_comments.py 149 --output comments.json
python3 coderabbit-tools/parse_coderabbit_comments_v2.py --input comments.json --output analysis.json
python3 coderabbit-tools/apply_coderabbit_fixes_v2.py --input analysis.json --dry-run
```

## Requirements

- Python 3.6+
- `gh` CLI installed and authenticated
- Git repository with GitHub remote

## Installation

### Method 1: Install as Python Package (Recommended)

```bash
# Clone the repository
git clone https://github.com/rshade/coderabbit-scripts.git
cd coderabbit-scripts

# Install in editable mode for development
pip install -e .

# Or install directly from GitHub
pip install git+https://github.com/rshade/coderabbit-scripts.git
```

After installation, the tools will be available as commands:
- `coderabbit-fetch`
- `coderabbit-parse`
- `coderabbit-apply`
- `coderabbit-pipeline`
- `coderabbit-fast`
- `coderabbit-ai-only`
- `coderabbit-ai-formatter`

### Method 2: Use Shell Scripts

```bash
# Clone the repository
git clone https://github.com/rshade/coderabbit-scripts.git
cd coderabbit-scripts

# Make shell scripts executable
chmod +x coderabbit-*

# Add to PATH (optional)
export PATH="$PATH:$(pwd)"
```

### Method 3: Manual Installation

1. Copy the `coderabbit-tools` directory to your project
2. Make Python scripts executable: `chmod +x coderabbit-tools/*.py`
3. Install and authenticate `gh` CLI: https://cli.github.com/

## Supported Fix Types

The tools automatically detect and categorize these fix types:

- **format_fix**: Missing backticks, markdown formatting issues
- **input_validation**: Parameter validation, range checks
- **error_handling**: Error message improvements, exception handling
- **test_fix**: Test coverage, test case additions
- **config_fix**: Configuration file corrections (YAML, etc.)
- **import_fix**: Missing imports, import corrections

## Cross-Repository Usage

These tools are designed to work across multiple repositories:

1. **Copy the tools** to a shared location (e.g., `~/bin/` or `~/.local/bin/`)
2. **Add to PATH** so they're available globally
3. **Use with any repo** by specifying the repository explicitly

Example for working with different repos:
```bash
# Process React repo (after pip install)
coderabbit-pipeline facebook/react 12345 --dry-run

# Process Go repo
coderabbit-pipeline golang/go 67890 --filter-type format_fix

# Process your own repos
coderabbit-pipeline yourusername/yourproject 123 --verbose
```

## Output Files

When using `--keep-files`, these files are generated:

- **github_comments.json**: Raw GitHub API responses
- **coderabbit_analysis.json**: Parsed CodeRabbit data with AI prompts

These files can be shared, archived, or used for further analysis.

## Examples from cronai PR #149

```bash
# See what the tools found (after pip install)
coderabbit-pipeline rshade/cronai 149 --summary-only

# Output:
# Found 40 CodeRabbit comments with AI prompts/suggestions
# By file (13 files):
#   .coderabbit.yaml: 3 comments
#   internal/queue/config_test.go: 4 comments
#   internal/queue/coordinator_test.go: 4 comments
#   ...

# Apply fixes in dry-run mode
coderabbit-pipeline rshade/cronai 149 --dry-run

# Output:
# Results:
#   Total comments: 40
#   Applied: 27
#   Failed: 3
#   Skipped: 10
```

This workflow identified and could apply fixes for issues like:
- Missing closing backticks in documentation
- Input validation in retry policies  
- Error message test expectations
- YAML configuration format issues
- Import statement corrections

## Troubleshooting

**gh CLI not found**: Install from https://cli.github.com/
**Permission denied**: Make scripts executable with `chmod +x *.py`
**Repository not found**: Ensure you have access to the repository
**No comments found**: The PR may not have CodeRabbit reviews

For verbose debugging, use `--verbose` flag with any tool.

If commands not found after installation:
```bash
source ~/.bashrc
# or
export PATH="$HOME/bin:$PATH"
```

Check installation:
```bash
ls -la ~/bin/coderabbit-*
ls -la ~/bin/coderabbit-tools/
```

Test with a known PR:
```bash
coderabbit-fetch rshade/cronai 149 --format summary
```

## Quick Reference

### Complete Pipeline (Recommended)
```bash
# Fix current repo
coderabbit-fix 149

# Fix specific repo
coderabbit-fix rshade/cronai 149

# Dry run (preview changes)
coderabbit-fix 149 --dry-run

# Filter by fix type
coderabbit-fix 149 --filter-type format_fix

# Verbose output
coderabbit-fix 149 --verbose

# Run linter validation
coderabbit-linter
```

### Common Workflows

#### 1. Quick Fix for Current Repo
```bash
cd /path/to/your/repo
coderabbit-fix 123 --dry-run
# If looks good, run without --dry-run
coderabbit-fix 123
```

#### 2. Fix Multiple Repos
```bash
# Fix React PR
coderabbit-fix facebook/react 12345 --dry-run

# Fix Go PR
coderabbit-fix golang/go 67890 --dry-run

# Fix your own repo
coderabbit-fix yourusername/yourproject 123
```

#### 3. Debug Mode
```bash
# Keep intermediate files
coderabbit-fix 149 --keep-files --output-dir ./debug

# Check what was found
cat ./debug/coderabbit_analysis.json | jq '.by_file'
```

#### 4. Manual Pipeline
```bash
# Step by step with inspection
coderabbit-fetch 149 --output comments.json
coderabbit-parse --input comments.json --output analysis.json
cat analysis.json | jq '.total_comments'
coderabbit-apply --input analysis.json --dry-run
```

#### 5. Validation Workflow
```bash
# Fix issues and validate
coderabbit-fix 149
coderabbit-linter --verbose
```

## Location of Tools

- Wrapper scripts: `~/bin/coderabbit-*` or `coderabbit-*` commands (if installed via pip)
- Python scripts: `~/bin/coderabbit-tools/*.py` or within the package
- Documentation: This README file