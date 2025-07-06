# CodeRabbit Linter

A comprehensive pre-commit linting system designed to catch common issues before they reach CodeRabbit review. This tool helps break the development cycle of commit → CodeRabbit flags issues → fix → recommit.

## Features

- **Multi-language support**: Go, Markdown, Node.js/YAML
- **Auto-fixing**: Automatically fixes formatting issues where possible
- **Modular design**: Language-specific linters organized by category
- **Priority-based reporting**: Issues categorized by High/Medium/Low priority
- **Integration-ready**: Works with external tools like `markdownlint-cli`

## Installation

```bash
# Install Python dependencies
pip install pyyaml

# Install markdownlint-cli for Markdown linting
npm install -g markdownlint-cli

# Clone or download the linter
git clone <repository-url>
cd coderabbit-tools
```

## Usage

### Basic Usage

```bash
# Lint current directory
python coderabbit_linter.py

# Lint specific project
python coderabbit_linter.py --path /path/to/project

# Auto-fix issues where possible
python coderabbit_linter.py --fix

# Run specific linters only
python coderabbit_linter.py --linters go_security,markdownlint

# List all available linters
python coderabbit_linter.py --list-linters
```

### Exit Codes

- `0`: No issues found or only low/medium priority issues
- `1`: High priority issues found that must be fixed

### Integration with Git Hooks

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
python /path/to/coderabbit_linter.py --path . --fix
exit_code=$?

if [ $exit_code -eq 1 ]; then
    echo "❌ Critical linting issues found. Commit aborted."
    echo "Run 'python coderabbit_linter.py --fix' to auto-fix issues."
    exit 1
fi
```

## Available Linters

### Go Linters

#### `go_module` - Go Module and Dependency Issues
- **Detects**: Incorrectly marked indirect dependencies, outdated packages
- **Fixes**: Removes incorrect `// indirect` comments
- **Example Issue**: `github.com/golang-jwt/jwt/v5` marked as indirect but directly imported

#### `go_security` - Security Vulnerabilities  
- **Detects**: Hardcoded secrets, JWT vulnerabilities, weak crypto, SQL injection
- **Priority**: High for secrets, Medium for crypto patterns
- **Example Issues**:
  - Default JWT signing keys: `"your-256-bit-secret"`
  - Hardcoded API keys: `"sk_live_..."`
  - `math/rand` for crypto purposes

#### `go_context` - Context Handling Patterns
- **Detects**: Missing context cancellation, timeout issues, poor propagation
- **Example Issues**:
  - Missing `ctx.Err()` checks in `Ping()` methods
  - `context.Background()` in non-main functions
  - Missing `defer cancel()` after `WithTimeout`

#### `go_format` - Code Formatting and Style
- **Detects**: Trailing whitespace, duplicate comments, line length
- **Auto-fixes**: Whitespace issues, duplicate comments, file endings
- **Example Issues**:
  - Duplicate function comments
  - Mixed tabs/spaces indentation
  - Missing newline at file end

#### `test` - Testing Best Practices
- **Detects**: Test function signatures, concurrency issues, assertion patterns
- **Example Issues**:
  - `t.Parallel()` in fuzz tests (causes deadlocks)
  - Unbuffered error channels in tests
  - Missing error handling in tests

### Markdown Linters

#### `markdownlint` - Markdown Formatting (External Tool)
- **Requires**: `markdownlint-cli` installed globally
- **Detects**: All standard markdownlint rules (MD001-MD047)
- **Auto-fixes**: End-of-file newlines, multiple blank lines, hard tabs
- **Priority Mapping**:
  - High: Structural issues (MD001, MD003, MD022, MD025)
  - Medium: Formatting consistency (MD004, MD009, MD013, MD040)
  - Low: Style preferences

### Node.js Linters

#### `node_package` - Package.json and Dependencies
- **Detects**: Missing required fields, version patterns, security issues, outdated deps
- **Integrates**: `npm outdated` for dependency checking
- **Example Issues**:
  - Missing `name` or `version` fields
  - Exact versions without range specifiers
  - Known vulnerable packages

#### `yaml` - YAML Formatting and CI/CD
- **Detects**: Syntax errors, formatting issues, GitHub Actions problems
- **Auto-fixes**: Trailing whitespace, tabs to spaces, file endings
- **GitHub Actions**: Outdated action versions, hardcoded secrets
- **Example Issues**:
  - Using `actions/checkout@v1` instead of `@v4`
  - Hardcoded secrets not using `${{ secrets.NAME }}`

## Architecture

### Base Classes

```
linters/
├── base_linter.py          # Base classes and interfaces
├── golang/                 # Go-specific linters
│   ├── go_module_linter.py
│   ├── security_linter.py
│   ├── context_linter.py
│   ├── format_linter.py
│   └── test_linter.py
├── markdown/               # Markdown linters
│   └── markdownlint_linter.py
└── nodejs/                 # Node.js linters
    ├── package_linter.py
    └── yaml_linter.py
```

### Key Classes

- **`BaseLinter`**: Abstract base class for all linters
- **`GoLinter`**: Base class for Go-specific linters (handles generated files)
- **`MarkdownLinter`**: Base class for Markdown linters
- **`NodeJSLinter`**: Base class for Node.js/JavaScript linters
- **`LintIssue`**: Data class representing a single issue
- **`LintSeverity`**: Enum for High/Medium/Low priority levels

### Adding New Linters

1. **Choose the appropriate base class** (`GoLinter`, `MarkdownLinter`, `NodeJSLinter`)
2. **Implement `lint_file()` method** for single-file analysis
3. **Add rule IDs and severity mapping** (e.g., `SEC_001`, `FMT_004`)
4. **Implement auto-fixing** in `_fix_issue()` if applicable
5. **Register in main linter** in `coderabbit_linter.py`

Example:

```python
class NewGoLinter(GoLinter):
    def __init__(self):
        super().__init__("new_linter")
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        issues = []
        # Implement linting logic
        return issues
```

## Rule ID Convention

- **Go**: `GO_xxx`, `SEC_xxx`, `CTX_xxx`, `FMT_xxx`, `TEST_xxx`
- **Markdown**: `MD_xxx` (following markdownlint)
- **Node.js**: `PKG_xxx` (package), `YAML_xxx` (YAML)

## Common Issues Detected

Based on analysis of 31 CodeRabbit issues, this linter catches:

### High Priority (Must Fix)
- Security vulnerabilities (hardcoded secrets, weak JWT)
- Syntax errors and compilation issues
- SQL injection vulnerabilities
- Missing required configuration

### Medium Priority (Should Fix)
- Performance issues (N+1 queries, inefficient patterns)
- Best practice violations (context handling, error checking)
- Dependency management (outdated versions, incorrect marking)
- Code organization and maintainability

### Low Priority (Nice to Fix)
- Formatting and style consistency
- Documentation completeness
- Code organization improvements
- Minor performance optimizations

## Performance

- **Fast**: Uses regex and AST-free parsing for speed
- **Parallel-ready**: Each linter runs independently
- **Scalable**: Skips generated files and common ignore patterns
- **Efficient**: Only reads files once per linter

## Integration Examples

### Pre-commit Hook
```bash
#!/bin/bash
python coderabbit_linter.py --fix --linters go_security,go_format,markdownlint
if [ $? -eq 1 ]; then exit 1; fi
```

### CI/CD Pipeline
```yaml
- name: Run CodeRabbit Linter
  run: |
    python coderabbit_linter.py --path .
    if [ $? -eq 1 ]; then
      echo "Critical issues found"
      exit 1
    fi
```

### Make Target
```makefile
lint-precommit:
	python tools/coderabbit_linter.py --fix
	@echo "✅ Linting complete"
```

## Contributing

1. Add new linters in appropriate language directories
2. Follow the base class patterns
3. Include auto-fixing where possible
4. Add comprehensive rule documentation
5. Test with real codebases

## Dependencies

- **Python 3.7+**: Core runtime
- **pyyaml**: YAML parsing for Node.js linter
- **markdownlint-cli** (optional): For markdown linting
- **npm/yarn** (optional): For Node.js dependency checking

## License

This tool is designed to complement CodeRabbit's AI-powered code review by catching common issues before they reach the review stage, improving development velocity and code quality.