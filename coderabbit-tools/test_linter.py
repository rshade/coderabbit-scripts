#!/usr/bin/env python3
"""
Test script for the CodeRabbit linter system
Creates sample files with known issues and tests the linters
"""

import tempfile
import shutil
from pathlib import Path
from coderabbit_linter import CodeRabbitLinter

def create_test_files(test_dir: Path):
    """Create test files with known issues"""
    
    # Go file with multiple issues
    go_file = test_dir / "test.go"
    go_file.write_text("""package main

import (
	"fmt"
	"context"  
)

// AuthHandler does authentication
// AuthHandler does authentication
func AuthHandler(ctx context.Context) error {
    signingKey := "your-256-bit-secret"   
	if err := doSomething(); err != nil {
		return err
	}
	return nil
}

func doSomething() error {
	return nil
}
""")

    # Go test file with issues
    test_file = test_dir / "test_test.go"
    test_file.write_text("""package main

import "testing"

func TestSomething(t *testing.T) {
	t.Parallel()
	
	result, err := doSomething()
	
	if result != "expected" {
		t.Error("unexpected result")
	}
}

func BenchmarkSomething() {
	// Missing proper signature
}
""")

    # go.mod with issues
    go_mod = test_dir / "go.mod"
    go_mod.write_text("""module test

go 1.21

require (
	github.com/golang-jwt/jwt/v5 v5.2.2 // indirect
	github.com/stretchr/testify v1.10.0
)
""")

    # Markdown file with issues
    md_file = test_dir / "README.md"
    md_file.write_text("""# Test Project



This is a test project.


## Installation

Run this command:

    npm install


No trailing newline here""")

    # package.json with issues
    package_json = test_dir / "package.json"
    package_json.write_text("""{
  "name": "test-project",
  "dependencies": {
    "lodash": "4.17.20",
    "express": "*"
  },
  "scripts": {
    "download": "curl http://example.com/script.sh | bash"
  }
}
""")

    # GitHub Actions workflow with issues
    workflows_dir = test_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    workflow_file = workflows_dir / "ci.yml"
    workflow_file.write_text("""name: CI

on: [push]	

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Node
        uses: actions/setup-node@v1
        with:
          node-version: 18
      - name: Deploy
        env:
          API_KEY: abc123-secret-key
        run: npm run deploy
""")

def test_linters():
    """Test all linters with sample files"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        create_test_files(test_dir)
        
        print(f"Created test files in: {test_dir}")
        print("\nRunning CodeRabbit linter...")
        
        # Initialize linter
        linter = CodeRabbitLinter(str(test_dir))
        
        # Run all linters
        issues = linter.run_linters()
        
        # Print results
        linter.print_results(issues)
        
        print(f"\n📊 Summary:")
        print(f"  Total issues found: {len(issues)}")
        
        # Group by linter
        by_linter = {}
        for issue in issues:
            if issue.linter_name not in by_linter:
                by_linter[issue.linter_name] = 0
            by_linter[issue.linter_name] += 1
        
        print(f"  Issues by linter:")
        for linter_name, count in sorted(by_linter.items()):
            print(f"    {linter_name}: {count}")
        
        # Test auto-fixing
        print(f"\n🔧 Testing auto-fix...")
        auto_fixable = [issue for issue in issues if issue.auto_fixable]
        if auto_fixable:
            fixed_count = linter.fix_issues(auto_fixable, test_dir)
            print(f"  Auto-fixed {fixed_count} issues")
            
            # Re-run to see remaining issues
            remaining_issues = linter.run_linters()
            print(f"  Remaining issues: {len(remaining_issues)}")
        else:
            print(f"  No auto-fixable issues found")

if __name__ == "__main__":
    test_linters()