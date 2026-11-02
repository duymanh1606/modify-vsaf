"""
Custom Ruff rules for VDS PDF Orchestrator enterprise compliance and security.

This module provides custom linting rules specific to:
- SOC 2 compliance requirements
- PII/PHI handling security
- Audit trail requirements
- Enterprise code quality standards
- Security best practices for PDF processing
"""

from __future__ import annotations

import ast
from collections.abc import Generator, Sequence
from typing import Any, ClassVar

from ruff.api import (
    LintResult,
    Rule,
    check,
)


class SOC2AuditTrailRule(Rule):
    """
    Ensure proper audit trail implementation for SOC 2 compliance.

    This rule checks that functions dealing with sensitive data
    have proper audit logging for compliance requirements.
    """

    code: str = "VDS001"
    message: str = "Missing audit trail logging for SOC 2 compliance"
    tags: ClassVar[set[str]] = {"security", "compliance", "soc2"}

    def __init__(self) -> None:
        self.audit_trail_functions = {
            "log",
            "audit",
            "track",
            "record",
            "capture",
            "audit_trail",
            "log_activity",
            "track_access",
        }

    @check
    def check(
        self, node: ast.AST, file: str, *args: Any, **kwargs: Any
    ) -> Generator[LintResult]:
        if not isinstance(node, ast.FunctionDef):
            return

        # Check if function handles sensitive data but lacks audit logging
        handles_sensitive = self._handles_sensitive_data(node)
        has_audit_logging = self._has_audit_logging(node)

        if handles_sensitive and not has_audit_logging:
            yield LintResult(
                node.lineno,
                node.col_offset,
                self.message,
                node,
            )

    def _handles_sensitive_data(self, node: ast.FunctionDef) -> bool:
        """Check if function handles PII, PHI, or other sensitive data."""
        sensitive_keywords = {
            "pii",
            "phi",
            "ssn",
            "credit_card",
            "password",
            "token",
            "secret",
            "credential",
            "personal_data",
            "user_data",
            "health_record",
            "medical",
            "financial",
            "payment",
            "authentication",
        }

        # Check function name
        func_name = node.name.lower()
        if any(keyword in func_name for keyword in sensitive_keywords):
            return True

        # Check parameters
        for arg in node.args.args:
            if any(keyword in arg.arg.lower() for keyword in sensitive_keywords):
                return True

        # Check function body for sensitive operations
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name):
                    name = stmt.func.id.lower()
                    if any(keyword in name for keyword in sensitive_keywords):
                        return True

        return False

    def _has_audit_logging(self, node: ast.FunctionDef) -> bool:
        """Check if function has audit logging."""
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name):
                    func_name = stmt.func.id
                    if func_name in self.audit_trail_functions:
                        return True
                elif isinstance(stmt.func, ast.Attribute):
                    attr_name = stmt.func.attr
                    if attr_name in self.audit_trail_functions:
                        return True

        return False


class EncryptionValidationRule(Rule):
    """
    Ensure proper encryption handling for sensitive data.

    This rule checks that encryption functions are used
    for sensitive data handling in compliance with SOC 2.
    """

    code: str = "VDS002"
    message: str = "Potential unencrypted sensitive data handling"
    tags: ClassVar[set[str]] = {"security", "compliance", "encryption"}

    @check
    def check(
        self, node: ast.AST, file: str, *args: Any, **kwargs: Any
    ) -> Generator[LintResult]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return

        # Check for patterns that might indicate unencrypted handling
        unencrypted_patterns = self._find_unencrypted_patterns(node)
        for pattern in unencrypted_patterns:
            yield LintResult(
                pattern["lineno"],
                pattern["col_offset"],
                f"{self.message}: {pattern['description']}",
                pattern["node"],
            )

    def _find_unencrypted_patterns(self, node: ast.FunctionDef) -> list[dict]:
        """Find patterns that might indicate unencrypted data handling."""
        patterns = []

        # Check for file operations without encryption
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name):
                    if stmt.func.id in ["open", "write", "save"]:
                        # Check if this is writing sensitive data
                        if self._is_writing_sensitive_data(stmt):
                            patterns.append(
                                {
                                    "lineno": stmt.lineno,
                                    "col_offset": stmt.col_offset,
                                    "node": stmt,
                                    "description": f"File operation '{stmt.func.id}' may write unencrypted sensitive data",
                                }
                            )

        return patterns

    def _is_writing_sensitive_data(self, call_node: ast.Call) -> bool:
        """Check if the call is writing potentially sensitive data."""
        # This is a simplified check - in practice, you'd want more sophisticated analysis

        # Check function name context
        return "write" in str(call_node).lower() or "save" in str(call_node).lower()


class ErrorHandlingRule(Rule):
    """
    Ensure proper error handling for security operations.

    This rule checks that security-critical functions
    have proper error handling to prevent information leakage.
    """

    code: str = "VDS003"
    message: str = "Insufficient error handling in security-critical function"
    tags: ClassVar[set[str]] = {"security", "error-handling", "compliance"}

    @check
    def check(
        self, node: ast.AST, file: str, *args: Any, **kwargs: Any
    ) -> Generator[LintResult]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return

        # Check if function is security-critical
        if self._is_security_critical(node):
            if not self._has_proper_error_handling(node):
                yield LintResult(
                    node.lineno,
                    node.col_offset,
                    self.message,
                    node,
                )

    def _is_security_critical(self, node: ast.FunctionDef) -> bool:
        """Check if function handles security-critical operations."""
        security_keywords = {
            "auth",
            "login",
            "authenticate",
            "validate",
            "secure",
            "encrypt",
            "decrypt",
            "verify",
            "check",
            "audit",
            "compliance",
            "risk",
            "security",
            "access",
            "permission",
            "authorization",
        }

        func_name = node.name.lower()
        return any(keyword in func_name for keyword in security_keywords)

    def _has_proper_error_handling(self, node: ast.FunctionDef) -> bool:
        """Check if function has proper error handling."""
        has_try_except = False
        has_logging = False

        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Try):
                has_try_except = True
                # Check if except block logs errors
                for handler in stmt.handlers:
                    if self._has_logging_in_handler(handler):
                        has_logging = True

            # Check for logging statements
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name):
                    if stmt.func.id in ["log", "logger", "error", "warn"]:
                        has_logging = True

        return has_try_except and has_logging

    def _has_logging_in_handler(self, handler: ast.ExceptHandler) -> bool:
        """Check if except handler has logging."""
        for stmt in ast.walk(handler):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name):
                    if stmt.func.id in ["log", "logger", "error", "warn", "exception"]:
                        return True
        return False


class InputValidationRule(Rule):
    """
    Ensure proper input validation for user inputs.

    This rule checks that functions accepting user input
    have proper validation to prevent injection attacks.
    """

    code: str = "VDS004"
    message: str = "Missing input validation for user-controlled data"
    tags: ClassVar[set[str]] = {"security", "input-validation", "compliance"}

    @check
    def check(
        self, node: ast.AST, file: str, *args: Any, **kwargs: Any
    ) -> Generator[LintResult]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return

        # Check if function accepts external input
        if self._accepts_external_input(node):
            if not self._has_input_validation(node):
                yield LintResult(
                    node.lineno,
                    node.col_offset,
                    self.message,
                    node,
                )

    def _accepts_external_input(self, node: ast.FunctionDef) -> bool:
        """Check if function accepts external input."""
        # Check parameter names that might indicate external input
        input_keywords = {
            "input",
            "data",
            "content",
            "file",
            "text",
            "user_input",
            "request",
            "payload",
            "query",
            "filename",
            "filepath",
            "path",
            "url",
        }

        for arg in node.args.args:
            if any(keyword in arg.arg.lower() for keyword in input_keywords):
                return True

        return False

    def _has_input_validation(self, node: ast.FunctionDef) -> bool:
        """Check if function has input validation."""
        validation_patterns = ["validate", "check", "verify", "sanitize", "clean"]

        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name):
                    func_name = stmt.func.id.lower()
                    if any(pattern in func_name for pattern in validation_patterns):
                        return True
                elif isinstance(stmt.func, ast.Attribute):
                    attr_name = stmt.func.attr.lower()
                    if any(pattern in attr_name for pattern in validation_patterns):
                        return True

        return False


# Rule registry
RULES = {
    "SOC2AuditTrailRule": SOC2AuditTrailRule,
    "EncryptionValidationRule": EncryptionValidationRule,
    "ErrorHandlingRule": ErrorHandlingRule,
    "InputValidationRule": InputValidationRule,
}


def get_rules() -> Sequence[Rule]:
    """Get all custom rules."""
    return list(RULES.values())
