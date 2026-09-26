#!/usr/bin/env python3
"""
SQL Security Checker for Frappe Framework

This script checks for SQL injection vulnerabilities and enforces secure SQL practices.

Existing violations can be accepted through a baseline file; see
scripts/baseline.py and the README section "Adopting on an existing codebase".
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional

try:
	from scripts.baseline import Violation
	from scripts.baseline import add_baseline_argument
	from scripts.baseline import apply_baseline
	from scripts.baseline import normalise_line
	from scripts.baseline import report
	from scripts.baseline import resolve_baseline
except ImportError:  # run directly as `python scripts/check_sql_security.py`
	from baseline import Violation
	from baseline import add_baseline_argument
	from baseline import apply_baseline
	from baseline import normalise_line
	from baseline import report
	from baseline import resolve_baseline

CHECK = "sql-security"

# Dangerous SQL patterns
DANGEROUS_PATTERNS = [
	(
		r'frappe\.db\.sql\s*\(\s*["\'][^"\']*\.format\s*\([^)]*\)',
		"SQL query using .format() - use parameterized queries with %s",
	),
	(
		r'frappe\.db\.sql\s*\(\s*["\'][^"\']*\{\}[^"\']*["\']',
		"SQL query with {} formatting - use %s parameters instead",
	),
	(
		r'frappe\.db\.sql\s*\(\s*["\'][^"\']*["\'][^,)]*\+',
		"SQL query with string concatenation - use parameterized queries",
	),
	(r'frappe\.db\.sql\s*\(\s*f["\']', "SQL query using f-strings - use parameterized queries with %s"),
	(
		r'frappe\.db\.sql\s*\(\s*["\'][^"\']*%[sd][^"\']*["\'][^,)]*%',
		"SQL query using % formatting - use parameterized queries",
	),
]

# Patterns for unencrypted sensitive data
ENCRYPTION_PATTERNS = [
	(
		r'frappe\.db\.set_value\s*\([^)]*password[^)]*["\'][^"\']+["\']',
		"Storing password without encryption - use frappe.utils.password.encrypt()",
	),
	(
		r'frappe\.db\.set_value\s*\([^)]*api_key[^)]*["\'][^"\']+["\']',
		"Storing API key without encryption - use frappe.utils.password.encrypt()",
	),
	(
		r'frappe\.db\.set_value\s*\([^)]*secret[^)]*["\'][^"\']+["\']',
		"Storing secret without encryption - use frappe.utils.password.encrypt()",
	),
]


def handles(file_path: str) -> bool:
	return file_path.endswith(".py")


def _read_lines(file_path: str) -> Optional[List[str]]:
	try:
		with open(file_path, encoding="utf-8") as f:
			return f.read().split("\n")
	except (UnicodeDecodeError, FileNotFoundError):
		return None


def _violation(file_path, rule, message, line_no, line) -> Violation:
	return Violation(
		path=file_path,
		check=CHECK,
		rule=rule,
		# The message is part of the key: one line can trip several patterns.
		key=f"{message} :: {normalise_line(line)}",
		line=line_no,
		message=f"Line {line_no}: {message}",
	)


def collect_violations(file_path: str) -> List[Violation]:
	"""Every SQL-security violation in one file."""
	lines = _read_lines(file_path)
	if lines is None:
		return []
	out: List[Violation] = []
	for i, line in enumerate(lines, 1):
		# Skip comments
		if line.strip().startswith("#"):
			continue

		if "frappe.db.sql" in line:
			for pattern, message in DANGEROUS_PATTERNS:
				if re.search(pattern, line, re.IGNORECASE):
					out.append(_violation(file_path, "sql-injection", message, i, line))
			# Complex SQL that should use Query Builder
			if any(k in line.upper() for k in ["JOIN", "UNION", "SUBQUERY"]) and len(line) > 120:
				out.append(
					_violation(
						file_path,
						"query-builder",
						"Consider using Query Builder for complex SQL queries",
						i,
						line,
					)
				)

		if "frappe.db.set_value" in line:
			for pattern, message in ENCRYPTION_PATTERNS:
				if re.search(pattern, line, re.IGNORECASE):
					out.append(_violation(file_path, "unencrypted-secret", message, i, line))
	return out


# Backwards-compatible helpers returning message strings, as in <= 1.0.5.


def check_sql_injection_patterns(file_path):
	return [
		v.message
		for v in collect_violations(file_path)
		if v.rule in ("sql-injection", "unencrypted-secret")
	]


def check_query_builder_usage(file_path):
	return [v.message for v in collect_violations(file_path) if v.rule == "query-builder"]


def check_permission_queries(file_path):
	"""Placeholder kept for API compatibility; it has never reported anything."""
	return []


FOOTER = [
	"💡 Security best practices:",
	"   ✅ Use parameterized queries: frappe.db.sql('SELECT * FROM tabUser WHERE name = %s', username)",
	"   ✅ Encrypt sensitive data: frappe.utils.password.encrypt(password)",
	"   ✅ Use Query Builder for complex queries",
	"   ✅ Always check permissions before data access",
]


def main(argv: Optional[List[str]] = None) -> int:
	"""Main function to process files"""
	parser = argparse.ArgumentParser(prog="frappe-pre-commit-sql-security")
	parser.add_argument("files", nargs="*")
	add_baseline_argument(parser)
	args = parser.parse_args(argv)
	if not args.files:
		print("Usage: check_sql_security.py [--baseline PATH] <file1> [file2] ...")
		return 0

	violations: List[Violation] = []
	for file_path in args.files:
		if Path(file_path).exists() and handles(file_path):
			violations.extend(collect_violations(file_path))

	baseline_path = resolve_baseline(args)
	new, suppressed = apply_baseline(violations, baseline_path)
	return report(new, suppressed, baseline_path, "❌ SQL security issues found:", FOOTER)


if __name__ == "__main__":
	sys.exit(main())
