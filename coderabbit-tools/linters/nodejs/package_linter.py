"""
Node.js package and dependency linter
Catches issues with package.json, outdated dependencies, security vulnerabilities
"""

import json
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any

from ..base_linter import NodeJSLinter, LintIssue, LintSeverity


class PackageLinter(NodeJSLinter):
    """Linter for Node.js package.json and dependencies"""
    
    def __init__(self):
        super().__init__("package", ["package.json", "package-lock.json", "yarn.lock"])
        self.npm_available = shutil.which('npm') is not None
        self.yarn_available = shutil.which('yarn') is not None
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint package.json files"""
        if file_path.name == "package.json":
            return self._lint_package_json(file_path)
        elif file_path.name in ["package-lock.json", "yarn.lock"]:
            return self._lint_lock_file(file_path)
        return []
    
    def _lint_package_json(self, file_path: Path) -> List[LintIssue]:
        """Analyze package.json for issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            # Check required fields
            issues.extend(self._check_required_fields(file_path, package_data))
            
            # Check dependency versions
            issues.extend(self._check_dependency_versions(file_path, package_data))
            
            # Check scripts
            issues.extend(self._check_scripts(file_path, package_data))
            
            # Check for security issues
            issues.extend(self._check_security_issues(file_path, package_data))
            
            # Check for outdated dependencies
            if self.npm_available:
                issues.extend(self._check_outdated_dependencies(file_path))
            
        except json.JSONDecodeError as e:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=1,
                severity=LintSeverity.HIGH,
                rule_id="PKG_001",
                message=f"Invalid JSON in package.json: {e}",
                suggestion="Fix JSON syntax errors"
            ))
        except Exception as e:
            print(f"Error linting {file_path}: {e}")
        
        return issues
    
    def _check_required_fields(self, file_path: Path, package_data: Dict[str, Any]) -> List[LintIssue]:
        """Check for required package.json fields"""
        issues = []
        
        required_fields = ["name", "version"]
        recommended_fields = ["description", "author", "license"]
        
        for field in required_fields:
            if field not in package_data:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.HIGH,
                    rule_id="PKG_002",
                    message=f"Missing required field: {field}",
                    suggestion=f"Add '{field}' field to package.json"
                ))
        
        for field in recommended_fields:
            if field not in package_data:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.LOW,
                    rule_id="PKG_003",
                    message=f"Missing recommended field: {field}",
                    suggestion=f"Add '{field}' field for better package metadata"
                ))
        
        return issues
    
    def _check_dependency_versions(self, file_path: Path, package_data: Dict[str, Any]) -> List[LintIssue]:
        """Check dependency version patterns"""
        issues = []
        
        deps_sections = ["dependencies", "devDependencies", "peerDependencies"]
        
        for section in deps_sections:
            if section not in package_data:
                continue
                
            dependencies = package_data[section]
            for dep_name, version in dependencies.items():
                # Check for exact versions without range specifiers
                if not any(char in str(version) for char in ['^', '~', '>', '<', '*', 'x']):
                    if str(version).count('.') == 2:  # Looks like exact version
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=1,
                            severity=LintSeverity.MEDIUM,
                            rule_id="PKG_004",
                            message=f"Exact version specified for {dep_name}: {version}",
                            suggestion=f"Consider using range specifier like ^{version}"
                        ))
                
                # Check for wildcard versions
                if '*' in str(version) or 'x' in str(version):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=1,
                        severity=LintSeverity.MEDIUM,
                        rule_id="PKG_005",
                        message=f"Wildcard version for {dep_name}: {version}",
                        suggestion="Use specific version ranges for better reproducibility"
                    ))
        
        return issues
    
    def _check_scripts(self, file_path: Path, package_data: Dict[str, Any]) -> List[LintIssue]:
        """Check npm scripts for issues"""
        issues = []
        
        if "scripts" not in package_data:
            return issues
        
        scripts = package_data["scripts"]
        
        # Check for common script patterns
        recommended_scripts = {
            "test": "npm test command",
            "lint": "code linting",
            "build": "build process"
        }
        
        for script_name, description in recommended_scripts.items():
            if script_name not in scripts:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.LOW,
                    rule_id="PKG_006",
                    message=f"Missing recommended script: {script_name}",
                    suggestion=f"Add '{script_name}' script for {description}"
                ))
        
        # Check for potential security issues in scripts
        for script_name, script_content in scripts.items():
            if 'curl' in script_content and 'http://' in script_content:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.MEDIUM,
                    rule_id="PKG_007",
                    message=f"Insecure HTTP URL in script '{script_name}'",
                    suggestion="Use HTTPS URLs for security"
                ))
        
        return issues
    
    def _check_security_issues(self, file_path: Path, package_data: Dict[str, Any]) -> List[LintIssue]:
        """Check for potential security issues"""
        issues = []
        
        # Check for known vulnerable packages (basic list)
        vulnerable_packages = {
            "event-stream": "Known malicious package",
            "getcookies": "Malicious package",
            "lodash": "Multiple vulnerabilities in older versions"
        }
        
        for section in ["dependencies", "devDependencies"]:
            if section not in package_data:
                continue
                
            dependencies = package_data[section]
            for dep_name in dependencies.keys():
                if dep_name in vulnerable_packages:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=1,
                        severity=LintSeverity.HIGH,
                        rule_id="PKG_008",
                        message=f"Potentially vulnerable package: {dep_name}",
                        suggestion=f"Review: {vulnerable_packages[dep_name]}"
                    ))
        
        return issues
    
    def _check_outdated_dependencies(self, file_path: Path) -> List[LintIssue]:
        """Check for outdated dependencies using npm"""
        issues = []
        
        try:
            result = subprocess.run(
                ['npm', 'outdated', '--json'],
                capture_output=True,
                text=True,
                cwd=file_path.parent,
                timeout=30
            )
            
            if result.stdout:
                try:
                    outdated_data = json.loads(result.stdout)
                    for package_name, info in outdated_data.items():
                        current = info.get('current', 'unknown')
                        wanted = info.get('wanted', 'unknown')
                        latest = info.get('latest', 'unknown')
                        
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=1,
                            severity=LintSeverity.LOW,
                            rule_id="PKG_009",
                            message=f"Outdated package: {package_name} ({current} -> {latest})",
                            suggestion=f"Update with: npm install {package_name}@{latest}"
                        ))
                except json.JSONDecodeError:
                    pass
                    
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass
        
        return issues
    
    def _lint_lock_file(self, file_path: Path) -> List[LintIssue]:
        """Check package lock files"""
        issues = []
        
        # Check if lock file is up to date with package.json
        package_json_path = file_path.parent / "package.json"
        if package_json_path.exists():
            lock_mtime = file_path.stat().st_mtime
            package_mtime = package_json_path.stat().st_mtime
            
            if package_mtime > lock_mtime:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.MEDIUM,
                    rule_id="PKG_010",
                    message="Lock file is older than package.json",
                    suggestion="Run npm install or yarn install to update lock file"
                ))
        
        return issues