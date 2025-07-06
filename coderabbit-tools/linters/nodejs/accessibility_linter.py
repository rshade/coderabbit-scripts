"""
Accessibility Linter - Catches accessibility issues in JavaScript/TypeScript/React

Focuses on ARIA attributes, semantic HTML, keyboard navigation, and screen reader support
"""

import re
from pathlib import Path
from typing import List

from ..base_linter import NodeJSLinter, LintIssue, LintSeverity


class AccessibilityLinter(NodeJSLinter):
    """Linter for accessibility (a11y) issues"""
    
    def __init__(self):
        super().__init__("accessibility", ["*.jsx", "*.tsx"])
    
    def lint_file(self, file_path: Path) -> List[LintIssue]:
        """Lint a React file for accessibility issues"""
        if not file_path.suffix in ['.jsx', '.tsx']:
            return []
            
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            # Only lint files that contain JSX
            if not self._contains_jsx(content):
                return []
                
            # Check for various accessibility issues
            issues.extend(self._check_missing_alt_text(file_path, lines))
            issues.extend(self._check_interactive_elements(file_path, lines))
            issues.extend(self._check_form_accessibility(file_path, lines))
            issues.extend(self._check_semantic_html(file_path, lines))
            issues.extend(self._check_aria_attributes(file_path, lines))
            issues.extend(self._check_color_contrast(file_path, lines))
            issues.extend(self._check_keyboard_navigation(file_path, lines))
            issues.extend(self._check_focus_management(file_path, lines))
            issues.extend(self._check_screen_reader_support(file_path, lines))
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
        return issues
    
    def _contains_jsx(self, content: str) -> bool:
        """Check if file contains JSX"""
        jsx_patterns = [
            r'<\w+[^>]*>',  # JSX tags
            r'</\w+>',      # Closing JSX tags
            r'React\.createElement',
            r'jsx\s*\(',
        ]
        
        return any(re.search(pattern, content) for pattern in jsx_patterns)
    
    def _check_missing_alt_text(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for images missing alt text"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for img tags without alt attribute
            if re.search(r'<img\s+', line) and 'alt=' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="a11y-missing-alt",
                    message="Image missing alt attribute",
                    suggestion="Add alt attribute with descriptive text, or alt=\"\" for decorative images"
                ))
            
            # Check for img with empty alt but no role="presentation"
            if re.search(r'alt\s*=\s*[\'\"]\s*[\'\""]', line) and 'role=' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="a11y-empty-alt",
                    message="Image with empty alt should have role=\"presentation\" for clarity",
                    suggestion="Add role=\"presentation\" to indicate decorative image"
                ))
            
            # Check for background images in CSS without text alternatives
            if re.search(r'backgroundImage\s*:', line) or re.search(r'background.*url\(', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="a11y-background-image",
                    message="Background images are not accessible to screen readers",
                    suggestion="Consider using <img> with alt text or provide alternative text content"
                ))
                
        return issues
    
    def _check_interactive_elements(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check interactive elements for accessibility"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for div/span with click handlers (should be button/link)
            interactive_patterns = [
                r'<div[^>]*onClick',
                r'<span[^>]*onClick',
                r'<p[^>]*onClick',
            ]
            
            for pattern in interactive_patterns:
                if re.search(pattern, line):
                    # Check if it has proper accessibility attributes
                    if not re.search(r'role\s*=\s*[\'\"](button|link)', line):
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.HIGH,
                            rule_id="a11y-interactive-element",
                            message="Interactive element should be a button or link, or have proper role",
                            suggestion="Use <button> or <a>, or add role=\"button\" and keyboard event handlers"
                        ))
            
            # Check for buttons without accessible text
            if re.search(r'<button[^>]*>', line):
                # Check if button has text content or aria-label
                if not re.search(r'aria-label\s*=|aria-labelledby\s*=', line):
                    # Look ahead for text content
                    has_text_content = False
                    for check_line_num in range(line_num, min(line_num + 3, len(lines))):
                        check_line = lines[check_line_num - 1]
                        if re.search(r'>\s*\w+', check_line) or re.search(r'{\w+}', check_line):
                            has_text_content = True
                            break
                    
                    if not has_text_content:
                        issues.append(self._create_issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=LintSeverity.HIGH,
                            rule_id="a11y-button-no-text",
                            message="Button missing accessible text",
                            suggestion="Add text content, aria-label, or aria-labelledby attribute"
                        ))
            
            # Check for links without text or aria-label
            if re.search(r'<a\s+', line) and not re.search(r'aria-label\s*=', line):
                if not re.search(r'>\s*\w+|{\w+}', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.HIGH,
                        rule_id="a11y-link-no-text",
                        message="Link missing accessible text",
                        suggestion="Add descriptive text content or aria-label attribute"
                    ))
                    
        return issues
    
    def _check_form_accessibility(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check form elements for accessibility"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for input without label
            if re.search(r'<input\s+', line):
                has_label_association = any([
                    'id=' in line and 'htmlFor=' in '\n'.join(lines[max(0, line_num-5):line_num+5]),
                    'aria-label=' in line,
                    'aria-labelledby=' in line,
                    'title=' in line
                ])
                
                if not has_label_association:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.HIGH,
                        rule_id="a11y-input-no-label",
                        message="Input missing associated label",
                        suggestion="Add label with htmlFor, aria-label, or aria-labelledby"
                    ))
            
            # Check for form without accessible name
            if re.search(r'<form\s*>', line) or re.search(r'<form\s+[^>]*>', line):
                if not re.search(r'aria-label\s*=|aria-labelledby\s*=', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="a11y-form-no-name",
                        message="Form missing accessible name",
                        suggestion="Add aria-label or aria-labelledby to describe form purpose"
                    ))
            
            # Check for select without label
            if re.search(r'<select\s+', line):
                if not re.search(r'aria-label\s*=|aria-labelledby\s*=', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.HIGH,
                        rule_id="a11y-select-no-label",
                        message="Select element missing label",
                        suggestion="Add aria-label or associate with label element"
                    ))
                    
        return issues
    
    def _check_semantic_html(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for proper semantic HTML usage"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for div soup (too many divs)
            div_count = line.count('<div')
            if div_count > 3:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="a11y-div-soup",
                    message="Consider using semantic HTML elements instead of multiple divs",
                    suggestion="Use <section>, <article>, <nav>, <header>, <main>, <aside>, <footer>"
                ))
            
            # Check for missing main landmark
            content = '\n'.join(lines)
            if 'function App(' in content or 'const App =' in content:
                if '<main' not in content and 'role="main"' not in content:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="a11y-missing-main",
                        message="Page missing main landmark",
                        suggestion="Add <main> element or role=\"main\" to identify main content"
                    ))
            
            # Check for headings hierarchy
            heading_match = re.search(r'<h([1-6])', line)
            if heading_match:
                heading_level = int(heading_match.group(1))
                if heading_level > 1:
                    # Basic check - this would need more sophisticated tracking
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.LOW,
                        rule_id="a11y-heading-hierarchy",
                        message=f"Ensure heading hierarchy is logical (h{heading_level} should follow h{heading_level-1})",
                        suggestion="Maintain logical heading order for screen reader navigation"
                    ))
                    
        return issues
    
    def _check_aria_attributes(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for proper ARIA attribute usage"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for invalid ARIA attributes
            aria_matches = re.findall(r'aria-(\w+)\s*=', line)
            valid_aria_attrs = {
                'label', 'labelledby', 'describedby', 'hidden', 'expanded', 'controls',
                'haspopup', 'selected', 'checked', 'disabled', 'required', 'invalid',
                'live', 'atomic', 'relevant', 'busy', 'dropeffect', 'grabbed',
                'activedescendant', 'owns', 'flowto', 'level', 'multiline',
                'multiselectable', 'orientation', 'readonly', 'sort', 'valuemax',
                'valuemin', 'valuenow', 'valuetext', 'autocomplete', 'keyshortcuts',
                'roledescription', 'placeholder', 'posinset', 'setsize'
            }
            
            for attr in aria_matches:
                if attr not in valid_aria_attrs:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="a11y-invalid-aria",
                        message=f"Invalid ARIA attribute: aria-{attr}",
                        suggestion="Use valid ARIA attributes from the ARIA specification"
                    ))
            
            # Check for redundant ARIA roles
            if re.search(r'<button[^>]*role\s*=\s*[\'\""]button[\'\""]', line):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.LOW,
                    rule_id="a11y-redundant-role",
                    message="Redundant role=\"button\" on button element",
                    suggestion="Remove redundant role attribute - button has implicit button role"
                ))
            
            # Check for aria-hidden on focusable elements
            if 'aria-hidden="true"' in line and any(attr in line for attr in ['tabindex', 'onClick', 'onFocus']):
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.HIGH,
                    rule_id="a11y-hidden-focusable",
                    message="Focusable element should not have aria-hidden=\"true\"",
                    suggestion="Remove aria-hidden or make element non-focusable"
                ))
                
        return issues
    
    def _check_color_contrast(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for potential color contrast issues"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for hardcoded colors that might have contrast issues
            color_patterns = [
                r'color\s*:\s*[\'\""]#[a-fA-F0-9]{3,6}[\'\""]',
                r'backgroundColor\s*:\s*[\'\""]#[a-fA-F0-9]{3,6}[\'\""]',
                r'style.*color.*#[a-fA-F0-9]{3,6}',
            ]
            
            for pattern in color_patterns:
                if re.search(pattern, line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.LOW,
                        rule_id="a11y-color-contrast",
                        message="Hardcoded colors may not meet contrast requirements",
                        suggestion="Use design system colors and test contrast ratios (4.5:1 minimum)"
                    ))
                    
        return issues
    
    def _check_keyboard_navigation(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for keyboard navigation support"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for elements with onClick but no onKeyDown
            if 'onClick=' in line and 'onKeyDown=' not in line:
                # Check if it's a proper interactive element
                if not re.search(r'<(button|a|input|select|textarea)', line):
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="a11y-keyboard-handler",
                        message="Interactive element missing keyboard event handler",
                        suggestion="Add onKeyDown handler for Enter/Space keys or use proper interactive element"
                    ))
            
            # Check for tabindex values other than 0 or -1
            tabindex_match = re.search(r'tabIndex\s*=\s*[\'\""]?(\d+)[\'\""]?', line)
            if tabindex_match:
                tabindex_value = int(tabindex_match.group(1))
                if tabindex_value > 0:
                    issues.append(self._create_issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=LintSeverity.MEDIUM,
                        rule_id="a11y-positive-tabindex",
                        message="Positive tabIndex values can create confusing tab order",
                        suggestion="Use tabIndex={0} to include in tab order or tabIndex={-1} to exclude"
                    ))
                    
        return issues
    
    def _check_focus_management(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for proper focus management"""
        issues = []
        
        content = '\n'.join(lines)
        
        # Check for modals without focus trapping
        if any(keyword in content.lower() for keyword in ['modal', 'dialog', 'popup']):
            if 'focus()' not in content and 'autoFocus' not in content:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=1,
                    severity=LintSeverity.MEDIUM,
                    rule_id="a11y-focus-management",
                    message="Modal/Dialog components should manage focus",
                    suggestion="Set initial focus and trap focus within modal"
                ))
        
        # Check for skip links
        if 'function App(' in content and 'skip' not in content.lower():
            issues.append(self._create_issue(
                file_path=file_path,
                line_number=1,
                severity=LintSeverity.LOW,
                rule_id="a11y-skip-link",
                message="Consider adding skip navigation link for keyboard users",
                suggestion="Add skip link to jump to main content"
            ))
            
        return issues
    
    def _check_screen_reader_support(self, file_path: Path, lines: List[str]) -> List[LintIssue]:
        """Check for screen reader support"""
        issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for elements that change without screen reader notification
            if re.search(r'display\s*:\s*[\'\""]none[\'\""]', line) and 'aria-hidden' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="a11y-screen-reader-hidden",
                    message="Hidden content should be properly announced to screen readers",
                    suggestion="Add aria-hidden=\"true\" or use sr-only class for screen reader only content"
                ))
            
            # Check for loading states without proper announcement
            if 'loading' in line.lower() and 'aria-live' not in line:
                issues.append(self._create_issue(
                    file_path=file_path,
                    line_number=line_num,
                    severity=LintSeverity.MEDIUM,
                    rule_id="a11y-loading-announcement",
                    message="Loading states should be announced to screen readers",
                    suggestion="Add aria-live=\"polite\" or aria-live=\"assertive\" for dynamic content"
                ))
                
        return issues