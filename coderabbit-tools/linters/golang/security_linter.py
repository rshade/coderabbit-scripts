"""
Go security linter
Catches security issues like hardcoded secrets, JWT vulnerabilities, etc.
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import GoLinter, LintIssue, LintSeverity


class SecurityLinter(GoLinter):
    """Linter for security vulnerabilities in Go code"""
    
    def __init__(self):
        super().__init__("security")
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Check Go file for security issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # Check for hardcoded secrets
                issues.extend(self._check_hardcoded_secrets(file_path, line_num, line))
                
                # Check for JWT security issues
                issues.extend(self._check_jwt_security(file_path, line_num, line))
                
                # Check for weak crypto
                issues.extend(self._check_weak_crypto(file_path, line_num, line))
                
                # Check for unsafe SQL
                issues.extend(self._check_sql_injection(file_path, line_num, line))
                
                # Check for insecure HTTP
                issues.extend(self._check_insecure_http(file_path, line_num, line))
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_hardcoded_secrets(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for hardcoded secrets and API keys"""
        issues = []
        
        # Skip test files for some checks
        is_test_file = file_path.name.endswith('_test.go')
        
        # Patterns for different types of secrets
        secret_patterns = [
            (r'["\']sk_live_[a-zA-Z0-9]{24,}["\']', 'Stripe live secret key'),
            (r'["\']sk_test_[a-zA-Z0-9]{24,}["\']', 'Stripe test secret key'),
            (r'["\']pk_live_[a-zA-Z0-9]{24,}["\']', 'Stripe live publishable key'),
            (r'["\']AKIA[0-9A-Z]{16}["\']', 'AWS access key'),
            (r'["\'][0-9a-zA-Z/+]{40}["\']', 'AWS secret key'),
            (r'["\']ya29\.[0-9A-Za-z\-_]+["\']', 'Google OAuth access token'),
            (r'["\']AIza[0-9A-Za-z\-_]{35}["\']', 'Google API key'),
            (r'["\']ghp_[A-Za-z0-9_]{36}["\']', 'GitHub personal access token'),
            (r'["\']ghs_[A-Za-z0-9_]{36}["\']', 'GitHub app token'),
        ]
        
        for pattern, secret_type in secret_patterns:
            if re.search(pattern, line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="SEC_001",
                    message=f"Hardcoded {secret_type} detected",
                    suggestion="Use environment variables or secure config management"
                ))
        
        # Generic high-entropy string check (but not in test files)
        if not is_test_file:
            # Look for suspicious variable assignments with high-entropy strings
            if re.search(r'(?:secret|key|token|password)\s*[:=]\s*["\'][A-Za-z0-9+/=]{20,}["\']', line, re.IGNORECASE):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="SEC_002",
                    message="Possible hardcoded secret or key",
                    suggestion="Verify this is not a real secret. Use environment variables for actual secrets."
                ))
        
        return issues
    
    def _check_jwt_security(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for JWT security issues"""
        issues = []
        
        # Check for default JWT signing keys
        if re.search(r'["\']your-.*-secret.*["\']', line, re.IGNORECASE):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.HIGH,
                rule_id="SEC_003",
                message="Default JWT signing key detected",
                suggestion="Use a secure, randomly generated signing key from environment variables"
            ))
        
        # Check for weak JWT algorithms
        if 'SigningMethodNone' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.HIGH,
                rule_id="SEC_004",
                message="JWT 'none' algorithm is insecure",
                suggestion="Use HMAC (HS256) or RSA (RS256) signing methods"
            ))
        
        # Check for missing JWT validation
        if 'ParseWithClaims' in line and 'WithValidMethods' not in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="SEC_005",
                message="JWT parsing without explicit algorithm validation",
                suggestion="Use jwt.WithValidMethods() to restrict allowed signing algorithms"
            ))
        
        # Check for missing clock skew handling
        if 'ParseWithClaims' in line or 'jwt.Parse' in line:
            if 'leeway' not in line.lower() and 'skew' not in line.lower():
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="SEC_012",
                    message="JWT parsing without clock skew handling",
                    suggestion="Add clock skew leeway (30s) for JWT timestamp validation"
                ))
        
        # Check for non-UTC time in JWT validation
        if 'time.Now()' in line and 'jwt' in line.lower():
            if '.UTC()' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="SEC_013",
                    message="JWT time validation should use UTC",
                    suggestion="Use time.Now().UTC() for consistent JWT timestamp validation"
                ))
        
        # Check for improper Bearer token parsing
        if 'Authorization' in line and 'Bearer' in line:
            if 'strings.HasPrefix' not in line and 'strings.ToLower' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="SEC_014",
                    message="Bearer token parsing without case-insensitive prefix check",
                    suggestion="Use case-insensitive Bearer token parsing with strings.ToLower()"
                ))
        
        # Check for missing JWT signing key environment variable requirement
        if 'JWT_SIGNING_KEY' in line and 'os.Getenv' in line:
            if 'log.Fatal' not in line and 'panic' not in line and 'err' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="SEC_015",
                    message="JWT signing key should be required environment variable",
                    suggestion="Fail fast with log.Fatal() if JWT_SIGNING_KEY is not set"
                ))
        
        # Check for missing error handling in JSON encoding
        if 'json.NewEncoder' in line and 'Encode' in line:
            if 'err' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="SEC_016",
                    message="JSON encoding without error handling",
                    suggestion="Handle JSON encoding errors and provide fallback response"
                ))
        
        return issues
    
    def _check_weak_crypto(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for weak cryptographic practices"""
        issues = []
        
        # Check for weak hash algorithms
        weak_hashes = ['md5', 'sha1']
        for weak_hash in weak_hashes:
            if f'crypto/{weak_hash}' in line or f'{weak_hash}.Sum' in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="SEC_006",
                    message=f"Weak hash algorithm {weak_hash.upper()} detected",
                    suggestion="Use SHA-256 or stronger hash algorithms"
                ))
        
        # Check for math/rand instead of crypto/rand
        if 'math/rand' in line and 'crypto' not in line:
            # Look for security-sensitive contexts
            if re.search(r'(?:token|key|secret|password|salt|nonce)', line, re.IGNORECASE):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="SEC_007",
                    message="Using math/rand for cryptographic purposes",
                    suggestion="Use crypto/rand for cryptographically secure random numbers"
                ))
        
        return issues
    
    def _check_sql_injection(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for potential SQL injection vulnerabilities"""
        issues = []
        
        # Check for string concatenation in SQL queries
        if re.search(r'(SELECT|INSERT|UPDATE|DELETE).*\+.*', line, re.IGNORECASE):
            if 'fmt.Sprintf' in line or '+' in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="SEC_008",
                    message="Potential SQL injection via string concatenation",
                    suggestion="Use parameterized queries with ? placeholders"
                ))
        
        # Check for fmt.Sprintf in SQL contexts
        if 'fmt.Sprintf' in line and re.search(r'(SELECT|INSERT|UPDATE|DELETE)', line, re.IGNORECASE):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="SEC_009",
                message="Using fmt.Sprintf for SQL query construction",
                suggestion="Use parameterized queries instead of string formatting"
            ))
        
        return issues
    
    def _check_insecure_http(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for insecure HTTP practices"""
        issues = []
        
        # Check for http:// URLs in production code
        if re.search(r'["\']http://(?!localhost|127\.0\.0\.1)', line):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="SEC_010",
                message="Insecure HTTP URL detected",
                suggestion="Use HTTPS for external URLs"
            ))
        
        # Check for disabled TLS verification
        if 'InsecureSkipVerify' in line and 'true' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.HIGH,
                rule_id="SEC_011",
                message="TLS certificate verification disabled",
                suggestion="Enable TLS verification for production code"
            ))
        
        return issues