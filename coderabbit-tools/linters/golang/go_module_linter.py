"""
Go module and dependency linter
Catches issues like indirect dependencies marked incorrectly, outdated versions
"""

import re
import subprocess
from pathlib import Path
from typing import List, Set

from ..base_linter import GoLinter, LintIssue, LintSeverity


class GoModuleLinter(GoLinter):
    """Linter for go.mod files and dependency management"""
    
    def __init__(self):
        super().__init__("go_module")
        self.file_patterns = ["go.mod", "*.go"]
    
    def lint(self, project_path: Path) -> List[LintIssue]:
        """Lint go.mod and detect dependency issues"""
        issues = []
        
        go_mod_path = project_path / "go.mod"
        if go_mod_path.exists():
            issues.extend(self._lint_go_mod(go_mod_path, project_path))
        
        return issues
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint individual Go files for import usage"""
        if file_path.name == "go.mod":
            return self._lint_go_mod(file_path, file_path.parent)
        return []
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Lint Go files - for GoModuleLinter, we don't lint individual Go files directly"""
        return []
    
    def _lint_go_mod(self, go_mod_path: Path, project_path: Path) -> List[LintIssue]:
        """Analyze go.mod for common issues"""
        issues = []
        
        try:
            with open(go_mod_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Get direct imports from Go files
            direct_imports = self._get_direct_imports(project_path)
            
            # Parse go.mod dependencies
            indirect_deps, direct_deps = self._parse_go_mod_dependencies(lines)
            
            # Check for incorrectly marked indirect dependencies
            for line_num, (dep, version) in enumerate(indirect_deps.items(), 1):
                if self._is_direct_dependency(dep, direct_imports):
                    issues.append(self._create_issue(
                        file_path=go_mod_path,
                        line_number=self._find_dependency_line(lines, dep),
                        severity=LintSeverity.MEDIUM,
                        rule_id="GO_MOD_001",
                        message=f"Dependency '{dep}' is marked as indirect but is directly imported",
                        suggestion=f"Remove '// indirect' comment from {dep}",
                        auto_fixable=True
                    ))
            
            # Check for outdated dependencies (if go list works)
            outdated_deps = self._check_outdated_dependencies(project_path)
            for dep, (current, latest) in outdated_deps.items():
                issues.append(self._create_issue(
                    file_path=go_mod_path,
                    line_number=self._find_dependency_line(lines, dep),
                    severity=LintSeverity.LOW,
                    rule_id="GO_MOD_002",
                    message=f"Dependency '{dep}' is outdated: {current} -> {latest}",
                    suggestion=f"Run 'go get {dep}@{latest}' to update"
                ))
                
        except Exception as e:
            print(f"Error linting {go_mod_path}: {e}")
        
        return issues
    
    def _get_direct_imports(self, project_path: Path) -> Set[str]:
        """Get all direct imports from Go files in the project"""
        imports = set()
        
        for go_file in project_path.rglob("*.go"):
            if self._should_skip_file(go_file) or self._is_generated_file(go_file):
                continue
                
            try:
                with open(go_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract imports using regex
                import_blocks = re.findall(r'import\s*\(\s*\n(.*?)\n\s*\)', content, re.DOTALL)
                single_imports = re.findall(r'import\s+"([^"]+)"', content)
                
                # Process import blocks
                for block in import_blocks:
                    for line in block.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('//'):
                            # Extract quoted import path
                            match = re.search(r'"([^"]+)"', line)
                            if match:
                                imports.add(match.group(1))
                
                # Process single imports
                imports.update(single_imports)
                
            except Exception:
                continue
        
        return imports
    
    def _parse_go_mod_dependencies(self, lines: List[str]) -> tuple:
        """Parse go.mod to extract direct and indirect dependencies"""
        indirect_deps = {}
        direct_deps = {}
        in_require_block = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('require ('):
                in_require_block = True
                continue
            elif line == ')' and in_require_block:
                in_require_block = False
                continue
            elif line.startswith('require ') and not in_require_block:
                # Single require line
                self._parse_require_line(line, direct_deps, indirect_deps)
            elif in_require_block and line and not line.startswith('//'):
                # Line within require block
                self._parse_require_line(line, direct_deps, indirect_deps)
        
        return indirect_deps, direct_deps
    
    def _parse_require_line(self, line: str, direct_deps: dict, indirect_deps: dict):
        """Parse a single require line"""
        # Remove 'require ' prefix if present
        line = re.sub(r'^require\s+', '', line)
        
        # Parse: module version [// indirect]
        parts = line.split()
        if len(parts) >= 2:
            module = parts[0]
            version = parts[1]
            is_indirect = '// indirect' in line
            
            if is_indirect:
                indirect_deps[module] = version
            else:
                direct_deps[module] = version
    
    def _is_direct_dependency(self, dep: str, direct_imports: Set[str]) -> bool:
        """Check if a dependency is directly imported"""
        # Check exact match
        if dep in direct_imports:
            return True
        
        # Check if any import starts with this dependency path
        for imp in direct_imports:
            if imp.startswith(dep + '/'):
                return True
        
        return False
    
    def _find_dependency_line(self, lines: List[str], dep: str) -> int:
        """Find the line number where a dependency is declared"""
        for i, line in enumerate(lines, 1):
            if dep in line and ('require' in line or not line.strip().startswith('//')):
                return i
        return 1
    
    def _check_outdated_dependencies(self, project_path: Path) -> dict:
        """Check for outdated dependencies using go list"""
        outdated = {}
        
        try:
            # Get current dependencies
            result = subprocess.run(
                ['go', 'list', '-m', '-u', 'all'],
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 3 and '[' in parts[2]:
                        module = parts[0]
                        current = parts[1]
                        # Extract latest version from [v1.2.3]
                        latest_match = re.search(r'\[([^\]]+)\]', parts[2])
                        if latest_match:
                            latest = latest_match.group(1)
                            outdated[module] = (current, latest)
                            
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            # If go list fails, just continue without outdated checks
            pass
        
        return outdated
    
    def _fix_issue(self, issue: LintIssue) -> bool:
        """Auto-fix go.mod issues"""
        if issue.rule_id == "GO_MOD_001":  # Remove incorrect // indirect
            try:
                with open(issue.file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Find and fix the line
                for i, line in enumerate(lines):
                    if issue.line_number - 1 == i and '// indirect' in line:
                        lines[i] = line.replace('// indirect', '').rstrip() + '\n'
                        
                        with open(issue.file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        return True
                        
            except Exception:
                pass
        
        return False