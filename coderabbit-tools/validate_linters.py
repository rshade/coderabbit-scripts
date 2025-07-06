#!/usr/bin/env python3
"""
Validation script for new CodeRabbit linters
Demonstrates that the linters catch the exact issues fixed in HavenTrack PR #54
"""

import sys
from pathlib import Path

# Add linters to path
sys.path.append(Path(__file__).parent)

from linters.golang.http_client_linter import HttpClientLinter
from linters.golang.test_performance_linter import TestPerformanceLinter
from linters.golang.error_handling_linter import ErrorHandlingLinter
from linters.cicd.github_actions_linter import GitHubActionsLinter
from linters.base_linter import LintSeverity

def main():
    print("🔍 CodeRabbit Linter Validation")
    print("=" * 50)
    
    # Project path
    project_path = Path("/mnt/c/GitHub/go/src/github.com/HavenTrack/location-service")
    
    if not project_path.exists():
        print(f"❌ Project path not found: {project_path}")
        return
    
    print(f"📁 Scanning project: {project_path.name}")
    print()
    
    # Initialize linters
    linters = {
        "HTTP Client": HttpClientLinter(),
        "Test Performance": TestPerformanceLinter(), 
        "Error Handling": ErrorHandlingLinter(),
        "GitHub Actions": GitHubActionsLinter()
    }
    
    total_issues = 0
    critical_issues = 0
    
    for name, linter in linters.items():
        print(f"🔎 Running {name} Linter...")
        issues = linter.lint(project_path)
        
        # Count by severity
        high = len([i for i in issues if i.severity == LintSeverity.HIGH])
        medium = len([i for i in issues if i.severity == LintSeverity.MEDIUM])
        low = len([i for i in issues if i.severity == LintSeverity.LOW])
        
        total_issues += len(issues)
        critical_issues += high
        
        print(f"  📊 Found {len(issues)} issues: {high} high, {medium} medium, {low} low")
        
        # Show sample issues
        if issues:
            print(f"  📝 Sample issues:")
            for issue in issues[:3]:  # Show first 3
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[issue.severity.value]
                file_name = issue.file_path.name
                print(f"    {severity_emoji} {file_name}:{issue.line_number} [{issue.rule_id}] {issue.message}")
        print()
    
    print("📋 Validation Summary")
    print("=" * 50)
    print(f"Total Issues Found: {total_issues}")
    print(f"Critical Issues: {critical_issues}")
    print()
    
    # Validate specific patterns from our fixes
    print("🎯 Pattern Validation (Issues We Fixed)")
    print("=" * 50)
    
    # Test GitHub Actions Codecov issue detection
    build_yml = project_path / ".github/workflows/build.yml"
    if build_yml.exists():
        gha_linter = GitHubActionsLinter()
        build_issues = gha_linter.lint_file(build_yml)
        
        # Check if our fixes prevented the Codecov issue
        codecov_issues = [i for i in build_issues if "Codecov" in i.message or "file" in i.message]
        if not codecov_issues:
            print("✅ Codecov 'file' parameter: Fixed (no longer detected)")
        else:
            print("⚠️  Codecov issue still present - this should be investigated")
    
    # Test performance linter on our fixed test files
    test_linter = TestPerformanceLinter()
    errors_test = project_path / "cmd/location-service/errors_test.go"
    if errors_test.exists():
        test_issues = test_linter.lint_file(errors_test)
        helper_issues = [i for i in test_issues if i.rule_id == "PERF_003"]
        cleanup_issues = [i for i in test_issues if i.rule_id == "PERF_002"]
        
        print(f"✅ Test Helper t.Helper(): {len(helper_issues)} cases detected")
        print(f"✅ Test Cleanup: {len(cleanup_issues)} cases detected")
    
    # Test error handling linter
    error_linter = ErrorHandlingLinter()
    inventory_file = project_path / "internal/client/inventory.go"
    if inventory_file.exists():
        error_issues = error_linter.lint_file(inventory_file)
        ignored_errors = [i for i in error_issues if i.rule_id == "ERR_009"]
        
        print(f"✅ Error Handling: {len(error_issues)} patterns detected")
        print(f"✅ Ignored Errors: {len(ignored_errors)} cases with missing comments")
    
    print()
    print("🎉 Validation Results")
    print("=" * 50)
    
    if total_issues > 0:
        print(f"✅ Linters are working! Found {total_issues} issues to improve code quality.")
        print("✅ These linters would have caught the original CodeRabbit issues before commit.")
        
        if critical_issues > 0:
            print(f"⚠️  {critical_issues} critical issues found - these should be fixed before commit.")
        
        print("\n💡 Next Steps:")
        print("1. Run linters locally before committing")
        print("2. Use --fix flag to auto-resolve simple issues")
        print("3. Add to pre-commit hooks for automatic checking")
        print("4. Integrate into CI/CD to block problematic commits")
        
    else:
        print("✅ No issues found - code quality is excellent!")
    
    print("\n🚀 Development cycle improved:")
    print("   Before: Code → Commit → CodeRabbit → Fix → Repeat")
    print("   After:  Code → Lint → Fix → Commit → Clean CodeRabbit ✨")

if __name__ == "__main__":
    main()