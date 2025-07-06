"""
Go Database Performance Linter
Catches N+1 queries, timeout issues, connection handling problems
Based on CodeRabbit issues: Fix #26 (N+1 queries), Fix #13 (timeouts), Fix #14 (DSN handling)
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import GoLinter, LintIssue, LintSeverity


class DatabasePerformanceLinter(GoLinter):
    """Linter for database performance and reliability issues in Go code"""
    
    def __init__(self):
        super().__init__("database_performance")
    
    def _lint_go_file(self, file_path: Path) -> List[LintIssue]:
        """Check Go file for database performance issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                # Check for N+1 query patterns
                issues.extend(self._check_n_plus_one_queries(file_path, line_num, line, content))
                
                # Check for missing timeouts
                issues.extend(self._check_missing_timeouts(file_path, line_num, line))
                
                # Check for DSN security issues
                issues.extend(self._check_dsn_security(file_path, line_num, line))
                
                # Check for connection pooling configuration
                issues.extend(self._check_connection_pooling(file_path, line_num, line))
                
                # Check for batch operation opportunities
                issues.extend(self._check_batch_opportunities(file_path, line_num, line))
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return issues
    
    def _check_n_plus_one_queries(self, file_path: Path, line_num: int, line: str, content: str) -> List[LintIssue]:
        """Check for N+1 query patterns"""
        issues = []
        
        # Look for loops with database queries inside
        if re.search(r'for\s+.*range', line):
            # Check next 10 lines for database operations
            lines = content.splitlines()
            start_idx = line_num - 1
            end_idx = min(start_idx + 10, len(lines))
            
            for i in range(start_idx + 1, end_idx):
                if i < len(lines):
                    loop_line = lines[i]
                    
                    # Look for database query patterns inside loops
                    db_patterns = [
                        r'\.Query\(',
                        r'\.QueryRow\(',
                        r'\.Exec\(',
                        r'\.Get\w*\(',
                        r'\.Find\w*\(',
                        r'\.Select\(',
                        r'db\.'
                    ]
                    
                    for pattern in db_patterns:
                        if re.search(pattern, loop_line):
                            issues.append(self._create_issue(
                                file_path=file_path,
                                line_number=line_num,
                                severity=LintSeverity.HIGH,
                                rule_id="DB_001",
                                message="Potential N+1 query detected - database operation inside loop",
                                suggestion="Consider using batch operations, JOINs, or IN clauses to fetch data in fewer queries"
                            ))
                            break
        
        # Check for individual GetXById calls that could be batched
        if re.search(r'Get\w*ById?\(', line) or re.search(r'Find\w*ById?\(', line):
            # Look for patterns like multiple individual ID fetches
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="DB_002",
                message="Individual ID-based query detected",
                suggestion="Consider implementing batch fetch methods like GetItemsBatch() for better performance"
            ))
        
        return issues
    
    def _check_missing_timeouts(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for missing database timeouts"""
        issues = []
        
        # Check for database operations without context timeout
        db_operations = [
            r'\.Ping\(',
            r'\.Query\(',
            r'\.QueryRow\(',
            r'\.Exec\(',
            r'sql\.Open\('
        ]
        
        for pattern in db_operations:
            if re.search(pattern, line):
                # Check if context is used
                if 'ctx' not in line and 'context' not in line:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="DB_003",
                        message="Database operation without context timeout",
                        suggestion="Use context.WithTimeout() for database operations to prevent hanging"
                    ))
                
                # Check for hardcoded short timeouts in tests
                if 'test' in file_path.name.lower() and re.search(r'[1-5]\s*\*\s*time\.Second', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="DB_004",
                        message="Short timeout in test may cause CI failures",
                        suggestion="Use 15s timeout for database tests to handle CI environment latency"
                    ))
        
        return issues
    
    def _check_dsn_security(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for DSN security and configuration issues"""
        issues = []
        
        # Check for hardcoded database credentials
        if re.search(r'["\'][^"\']*://[^:]+:[^@]+@[^"\']+["\']', line):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.HIGH,
                rule_id="DB_005",
                message="Hardcoded database credentials in DSN",
                suggestion="Use environment variables for database credentials"
            ))
        
        # Check for missing parseTime=true in MySQL DSN
        if 'mysql' in line.lower() and 'dsn' in line.lower():
            if 'parseTime=true' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="DB_006",
                    message="MySQL DSN missing parseTime=true parameter",
                    suggestion="Add parseTime=true to DSN for proper time.Time handling"
                ))
        
        # Check for DSN with database name in test setup
        if 'test' in file_path.name.lower() and re.search(r'["\'][^"\']*@tcp\([^)]+\)/\w+[?"\']', line):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="DB_007",
                message="Test DSN includes database name",
                suggestion="Remove database name from DSN to allow dynamic database creation in tests"
            ))
        
        return issues
    
    def _check_connection_pooling(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for connection pooling configuration"""
        issues = []
        
        # Check for missing connection pool configuration
        if 'sql.Open' in line and 'mysql' in line.lower():
            # Look for missing SetMaxOpenConns, SetMaxIdleConns calls
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="DB_008",
                message="Database connection opened without pool configuration",
                suggestion="Configure connection pool with SetMaxOpenConns(), SetMaxIdleConns(), and SetConnMaxLifetime()"
            ))
        
        # Check for excessive connection pool sizes
        if re.search(r'SetMaxOpenConns\(\s*([5-9]\d{2,}|\d{4,})', line):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="DB_009",
                message="Very high max open connections configured",
                suggestion="Consider lower connection pool sizes (25-100) unless handling very high load"
            ))
        
        return issues
    
    def _check_batch_opportunities(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for opportunities to use batch operations"""
        issues = []
        
        # Look for multiple individual INSERT/UPDATE statements
        if re.search(r'INSERT\s+INTO', line, re.IGNORECASE):
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.LOW,
                rule_id="DB_010",
                message="Individual INSERT statement detected",
                suggestion="Consider batch INSERT for multiple rows to improve performance"
            ))
        
        # Check for missing MIME type detection
        if 'DetectContentType' not in line and 'content.*type' in line.lower():
            if 'upload' in line.lower() or 'file' in line.lower():
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="DB_011",
                    message="File upload without dynamic MIME type detection",
                    suggestion="Use http.DetectContentType() for dynamic MIME type detection"
                ))
        
        return issues
    
    def _check_transaction_patterns(self, file_path: Path, line_num: int, line: str) -> List[LintIssue]:
        """Check for proper transaction handling"""
        issues = []
        
        # Check for missing transaction rollback
        if 'Begin()' in line or 'BeginTx(' in line:
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=line_num,
                severity=LintSeverity.MEDIUM,
                rule_id="DB_012",
                message="Transaction started - ensure proper rollback handling",
                suggestion="Use defer tx.Rollback() with error checking pattern for transaction safety"
            ))
        
        return issues