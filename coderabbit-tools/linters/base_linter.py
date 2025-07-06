"""
Base linter classes and utilities for the CodeRabbit linting system
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any


class LintSeverity(Enum):
    """Severity levels matching CodeRabbit's priority system"""
    HIGH = "high"      # Critical security/functionality issues
    MEDIUM = "medium"  # Performance, best practices
    LOW = "low"        # Style, documentation


@dataclass
class LintIssue:
    """Represents a single linting issue found in code"""
    file_path: Path
    line_number: int
    severity: LintSeverity
    linter_name: str
    rule_id: str
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    
    def __str__(self) -> str:
        severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[self.severity.value]
        return f"{severity_emoji} {self.file_path}:{self.line_number} [{self.rule_id}] {self.message}"


class BaseLinter(ABC):
    """Base class for all language-specific linters"""
    
    def __init__(self, name: str, file_patterns: List[str]):
        self.name = name
        self.file_patterns = file_patterns
        
    @abstractmethod
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint a single file and return issues found"""
        pass
    
    def lint(self, project_path: Path) -> List[LintIssue]:
        """Lint all applicable files in a project"""
        all_issues = []
        
        for pattern in self.file_patterns:
            for file_path in project_path.rglob(pattern):
                # Skip certain directories
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    issues = self.lint_file(file_path)
                    all_issues.extend(issues)
                except Exception as e:
                    # Log error but continue linting other files
                    print(f"Warning: Error linting {file_path}: {e}")
                    
        return all_issues
    
    def fix_issues(self, issues: List[LintIssue], project_path: Path) -> int:
        """Auto-fix issues where possible. Returns count of fixed issues."""
        fixed_count = 0
        
        for issue in issues:
            if issue.auto_fixable:
                try:
                    if self._fix_issue(issue):
                        fixed_count += 1
                except Exception as e:
                    print(f"Warning: Could not auto-fix {issue.file_path}:{issue.line_number}: {e}")
                    
        return fixed_count
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during linting"""
        skip_dirs = {
            '.git', 'node_modules', 'vendor', '.vscode', '.idea',
            'gen', '__pycache__', '.pytest_cache', 'dist', 'build'
        }
        
        # Check if any parent directory should be skipped
        for parent in file_path.parents:
            if parent.name in skip_dirs:
                return True
                
        return False
    
    def _fix_issue(self, issue: LintIssue) -> bool:
        """Override in subclasses to implement auto-fixing"""
        return False
    
    def _create_issue(self, file_path: Path, line_number: int, severity: LintSeverity, 
                     rule_id: str, message: str, suggestion: str = None, 
                     auto_fixable: bool = False) -> LintIssue:
        """Helper to create LintIssue objects"""
        return LintIssue(
            file_path=file_path,
            line_number=line_number,
            severity=severity,
            linter_name=self.name,
            rule_id=rule_id,
            message=message,
            suggestion=suggestion,
            auto_fixable=auto_fixable
        )


class GoLinter(BaseLinter):
    """Base class for Go-specific linters"""
    
    def __init__(self, name: str):
        super().__init__(name, ["*.go"])
        
    def _is_generated_file(self, file_path: Path) -> bool:
        """Check if Go file is generated (should be skipped)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
                for line in first_lines:
                    if 'Code generated' in line or 'DO NOT EDIT' in line:
                        return True
        except Exception:
            pass
        return False
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        if self._is_generated_file(file_path):
            return []
        return self._lint_go_file(file_path)
    
    @abstractmethod
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Implement Go-specific linting logic"""
        pass


class MarkdownLinter(BaseLinter):
    """Base class for Markdown-specific linters"""
    
    def __init__(self, name: str):
        super().__init__(name, ["*.md", "*.markdown"])


class NodeJSLinter(BaseLinter):
    """Base class for Node.js/JavaScript-specific linters"""
    
    def __init__(self, name: str, patterns: List[str] = None):
        patterns = patterns or ["*.js", "*.ts", "*.json", "package.json", "*.yml", "*.yaml"]
        super().__init__(name, patterns)