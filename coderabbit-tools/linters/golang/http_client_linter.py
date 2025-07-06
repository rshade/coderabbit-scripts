"""
Go HTTP client linter
Catches issues with HTTP client configuration, timeout patterns, and URL handling
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import GoLinter, LintIssue, LintSeverity


class HttpClientLinter(GoLinter):
    """Linter for HTTP client configuration and patterns"""
    
    def __init__(self):
        super().__init__("http_client")
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Check Go file for HTTP client issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                # Check HTTP client patterns
                issues.extend(self._check_timeout_patterns(file_path, line_num, line))
                issues.extend(self._check_url_patterns(file_path, line_num, line))
                issues.extend(self._check_memory_protection(file_path, line_num, line))
                issues.extend(self._check_error_patterns(file_path, line_num, line))
                
            # Check for hardcoded URLs that should be constants
            issues.extend(self._check_hardcoded_urls(file_path, content))
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_timeout_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for timeout configuration anti-patterns"""
        issues = []
        
        # HTTP client with timeout instead of context control
        if 'http.Client{' in line and 'Timeout:' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="HTTP_001",
                message="HTTP client timeout should be controlled via context, not client configuration",
                suggestion="Remove Timeout field and use context.WithTimeout() for requests",
                auto_fixable=False
            ))
        
        # Check for deprecated timeout configuration patterns
        if re.search(r'(Timeout|timeout)\s*:\s*\w+', line) and 'Config' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="HTTP_002",
                message="Deprecated timeout configuration detected",
                suggestion="Use context-based timeout control for better request management",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_url_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for URL handling patterns"""
        issues = []
        
        # String concatenation for URLs
        if '+' in line and ('http://' in line or 'https://' in line):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="HTTP_003",
                message="URL string concatenation detected",
                suggestion="Use url.Parse() and ResolveReference() for proper URL construction",
                auto_fixable=False
            ))
        
        # Missing URL validation
        if 'url.Parse(' in line and 'err' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.HIGH,
                rule_id="HTTP_004",
                message="URL parsing without error handling",
                suggestion="Always check error return from url.Parse()",
                auto_fixable=False
            ))
        
        # BaseURL validation patterns
        if 'BaseURL' in line and 'empty' not in line and 'nil' not in line:
            # Look for configuration without validation
            if 'Config' in line and 'panic' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="HTTP_005",
                    message="BaseURL configuration without validation",
                    suggestion="Validate BaseURL is non-empty and has proper scheme/host",
                    auto_fixable=False
                ))
        
        return issues
    
    def _check_memory_protection(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for memory protection patterns"""
        issues = []
        
        # JSON decoding without size limits
        if 'json.NewDecoder(' in line and 'io.LimitReader' not in line and 'resp.Body' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.HIGH,
                rule_id="HTTP_006",
                message="JSON decoding without memory protection",
                suggestion="Use io.LimitReader to prevent memory exhaustion: "
                          "json.NewDecoder(io.LimitReader(resp.Body, maxSize))",
                auto_fixable=False
            ))
        
        # Missing response body limits
        if 'ioutil.ReadAll(' in line and 'resp.Body' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.HIGH,
                rule_id="HTTP_007",
                message="Reading response body without size limit",
                suggestion="Use io.LimitReader to prevent memory exhaustion",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_error_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for error handling patterns"""
        issues = []
        
        # Direct error struct return instead of sentinel error wrapping
        if re.search(r'return.*&\w+Error{', line) and 'fmt.Errorf' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="HTTP_008",
                message="Direct error struct return without sentinel error wrapping",
                suggestion="Use fmt.Errorf(\"%w: %w\", ErrSentinel, &CustomError{}) for better error handling",
                auto_fixable=False
            ))
        
        # HTTP status code handling without proper error wrapping
        if 'StatusCode' in line and 'fmt.Errorf' in line and '%w' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="HTTP_009",
                message="HTTP status error without proper error wrapping",
                suggestion="Use %w verb in fmt.Errorf for error wrapping",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_hardcoded_urls(self, file_path: Path, content: str) -> List[LintIssue]:
        """Check for hardcoded URLs that should be constants"""
        issues = []
        
        # Find hardcoded HTTP URLs in string literals (not in constants)
        lines = content.splitlines()
        in_const_block = False
        
        for line_num, line in enumerate(lines, 1):
            # Track const blocks
            if line.strip().startswith('const'):
                in_const_block = True
                continue
            elif line.strip() == ')' and in_const_block:
                in_const_block = False
                continue
            elif line.strip() == '' or line.strip().startswith('//'):
                continue
            
            # Skip if we're in a const block or if line defines a const
            if in_const_block or 'const ' in line:
                continue
                
            # Look for hardcoded URLs in assignments or function calls
            url_match = re.search(r'["\']https?://[^"\']+["\']', line)
            if url_match and not re.search(r'//.*https?://', line):  # Skip comments
                url = url_match.group()
                # Skip localhost and test URLs
                if 'localhost' not in url and '127.0.0.1' not in url and 'example.com' not in url:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="HTTP_010",
                        message=f"Hardcoded URL {url} should be extracted to a constant",
                        suggestion="Define as const or load from environment variable",
                        auto_fixable=False
                    ))
        
        return issues