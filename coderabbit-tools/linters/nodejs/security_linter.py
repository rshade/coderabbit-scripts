"""
Node.js Security Linter - Catches common security vulnerabilities in JavaScript/TypeScript

Focuses on XSS, injection attacks, insecure data handling, and other security issues
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import NodeJSLinter, LintIssue, LintSeverity


class NodeJSSecurityLinter(NodeJSLinter):
    """Linter for Node.js/JavaScript security vulnerabilities"""
    
    def __init__(self):
        super().__init__("nodejs_security", ["*.js", "*.ts", "*.jsx", "*.tsx"])
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint a JavaScript/TypeScript file for security issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            # Check for various security issues
            issues.extend(self._check_dangerous_html_methods(file_path, lines))
            issues.extend(self._check_eval_usage(file_path, lines))
            issues.extend(self._check_hardcoded_secrets(file_path, lines))
            issues.extend(self._check_unsafe_url_construction(file_path, lines))
            issues.extend(self._check_insecure_random(file_path, lines))
            issues.extend(self._check_prototype_pollution(file_path, lines))
            issues.extend(self._check_unsafe_redirects(file_path, lines))
            issues.extend(self._check_jwt_vulnerabilities(file_path, lines))
            issues.extend(self._check_cors_misconfig(file_path, lines))
            issues.extend(self._check_sql_injection_risk(file_path, lines))
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
        return issues
    
    def _check_dangerous_html_methods(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for dangerous HTML manipulation methods"""
        issues = []
        
        dangerous_patterns = [
            (r'\.innerHTML\s*=', 'innerHTML', 'Use textContent or sanitize HTML with DOMPurify'),
            (r'\.outerHTML\s*=', 'outerHTML', 'Use safer DOM manipulation methods'),
            (r'dangerouslySetInnerHTML', 'dangerouslySetInnerHTML', 'Sanitize HTML content before using dangerouslySetInnerHTML'),
            (r'document\.write\s*\(', 'document.write', 'Use modern DOM manipulation instead of document.write'),
            (r'eval\s*\(', 'eval', 'Avoid eval() - use safer alternatives like JSON.parse()'),
            (r'new Function\s*\(', 'Function constructor', 'Avoid Function constructor - use regular functions'),
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern, method_name, suggestion in dangerous_patterns:
                if re.search(pattern, line):
                    # Skip if line has sanitization comment
                    if 'sanitized' in line.lower() or 'safe' in line.lower():
                        continue
                        
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.HIGH,
                        rule_id="security-dangerous-html",
                        message=f"Potentially dangerous use of {method_name}",
                        suggestion=suggestion
                    ))
                    
        return issues
    
    def _check_eval_usage(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for eval and related dangerous functions"""
        issues = []
        
        eval_patterns = [
            r'\beval\s*\(',
            r'setTimeout\s*\(\s*[\'"][^\'\"]*[\'"]',  # setTimeout with string
            r'setInterval\s*\(\s*[\'"][^\'\"]*[\'"]', # setInterval with string
            r'new Function\s*\(',
            r'execScript\s*\(',
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern in eval_patterns:
                if re.search(pattern, line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.HIGH,
                        rule_id="security-eval-usage",
                        message="Avoid eval-like functions that execute arbitrary code",
                        suggestion="Use safer alternatives like JSON.parse() or proper function calls"
                    ))
                    
        return issues
    
    def _check_hardcoded_secrets(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for hardcoded secrets, API keys, and passwords"""
        issues = []
        
        secret_patterns = [
            (r'(?i)(password|pwd|pass)\s*[:=]\s*[\'"][^\'\"]{8,}[\'"]', 'password'),
            (r'(?i)(api_?key|apikey)\s*[:=]\s*[\'"][^\'\"]{10,}[\'"]', 'API key'),
            (r'(?i)(secret|token)\s*[:=]\s*[\'"][^\'\"]{16,}[\'"]', 'secret/token'),
            (r'(?i)(private_?key|privatekey)\s*[:=]\s*[\'"][^\'\"]{20,}[\'"]', 'private key'),
            (r'[\'"][A-Za-z0-9]{32,}[\'"]', 'potential secret'),
        ]
        
        for line_num, line in enumerate(lines, 1):
            # Skip test files and mock data
            if any(word in file_path.name.lower() for word in ['test', 'spec', 'mock', 'fixture']):
                continue
                
            for pattern, secret_type in secret_patterns:
                if re.search(pattern, line):
                    # Skip if it's clearly a placeholder or example
                    if any(placeholder in line.lower() for placeholder in [
                        'your_', 'example', 'placeholder', 'dummy', 'fake', 'test'
                    ]):
                        continue
                        
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.HIGH,
                        rule_id="security-hardcoded-secret",
                        message=f"Potential hardcoded {secret_type} detected",
                        suggestion="Move secrets to environment variables or secure configuration"
                    ))
                    
        return issues
    
    def _check_unsafe_url_construction(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for unsafe URL construction that could lead to attacks"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for URL construction with user input
            unsafe_patterns = [
                r'window\.location\s*=\s*.*\+',        # window.location = ... + userInput
                r'location\.href\s*=\s*.*\+',          # location.href = ... + userInput
                r'window\.open\s*\(.*\+',              # window.open(... + userInput)
                r'fetch\s*\(.*\+',                     # fetch(... + userInput)
                r'axios\.\w+\s*\(.*\+',                # axios.get(... + userInput)
            ]
            
            for pattern in unsafe_patterns:
                if re.search(pattern, line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="security-unsafe-url",
                        message="Unsafe URL construction with concatenation",
                        suggestion="Use URL constructor or validate/sanitize input before URL construction"
                    ))
                    
        return issues
    
    def _check_insecure_random(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for insecure random number generation"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            if 'Math.random()' in line:
                # Check if it's being used for security purposes
                security_keywords = ['token', 'key', 'id', 'session', 'auth', 'password']
                if any(keyword in line.lower() for keyword in security_keywords):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="security-insecure-random",
                        message="Math.random() is not cryptographically secure",
                        suggestion="Use crypto.randomBytes() or window.crypto.getRandomValues() for security purposes"
                    ))
                    
        return issues
    
    def _check_prototype_pollution(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for prototype pollution vulnerabilities"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for dangerous object property assignment
            pollution_patterns = [
                r'\w+\[.*\]\s*=',                     # obj[userInput] = value
                r'Object\.assign\s*\(',               # Object.assign with user input
                r'\.prototype\s*\[.*\]\s*=',          # prototype[userInput] = value
                r'merge\s*\(',                        # lodash merge with user input
            ]
            
            for pattern in pollution_patterns:
                if re.search(pattern, line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="security-prototype-pollution",
                        message="Potential prototype pollution vulnerability",
                        suggestion="Validate object keys and avoid setting properties with user-controlled keys"
                    ))
                    
        return issues
    
    def _check_unsafe_redirects(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for unsafe redirects"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for redirects with user input
            if re.search(r'redirect\s*\(.*\+', line) or re.search(r'location\.href\s*=.*\+', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="security-unsafe-redirect",
                    message="Unsafe redirect with user input",
                    suggestion="Validate redirect URLs against allowlist or use relative URLs only"
                ))
                
        return issues
    
    def _check_jwt_vulnerabilities(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for JWT handling vulnerabilities"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for JWT without signature verification
            if 'jwt.decode' in line and 'verify' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="security-jwt-no-verify",
                    message="JWT decoded without signature verification",
                    suggestion="Always verify JWT signatures in production code"
                ))
            
            # Check for JWT in localStorage
            if 'localStorage' in line and ('token' in line.lower() or 'jwt' in line.lower()):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="security-jwt-localstorage",
                    message="JWT stored in localStorage is vulnerable to XSS",
                    suggestion="Consider using httpOnly cookies or secure session storage"
                ))
                
        return issues
    
    def _check_cors_misconfig(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for CORS misconfigurations"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for overly permissive CORS
            cors_patterns = [
                r'Access-Control-Allow-Origin.*\*',
                r'origin:\s*[\'\"]\*[\'\""]',
                r'cors\s*\(\s*\{.*origin:\s*true',
            ]
            
            for pattern in cors_patterns:
                if re.search(pattern, line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="security-cors-wildcard",
                        message="Overly permissive CORS configuration",
                        suggestion="Specify allowed origins explicitly instead of using wildcards"
                    ))
                    
        return issues
    
    def _check_sql_injection_risk(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for SQL injection risks"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for string concatenation in SQL queries
            sql_patterns = [
                r'SELECT.*\+.*',
                r'INSERT.*\+.*',
                r'UPDATE.*\+.*',
                r'DELETE.*\+.*',
                r'query\s*\(.*\+.*\)',
            ]
            
            for pattern in sql_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.HIGH,
                        rule_id="security-sql-injection",
                        message="Potential SQL injection vulnerability",
                        suggestion="Use parameterized queries or prepared statements instead of string concatenation"
                    ))
                    
        return issues