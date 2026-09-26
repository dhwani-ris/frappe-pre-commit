#!/usr/bin/env python3
"""
General Coding Standards Checker for Frappe Framework

This script checks for general coding standards compliance including:
- Function length
- Naming conventions
- Import placement
- Nesting depth and line length
- Deprecated Frappe patterns

Existing violations can be accepted through a baseline file; see
scripts/baseline.py and the README section "Adopting on an existing codebase".
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
	from scripts.baseline import Violation
	from scripts.baseline import add_baseline_argument
	from scripts.baseline import apply_baseline
	from scripts.baseline import normalise_line
	from scripts.baseline import report
	from scripts.baseline import resolve_baseline
except ImportError:  # run directly as `python scripts/check_coding_standards.py`
	from baseline import Violation
	from baseline import add_baseline_argument
	from baseline import apply_baseline
	from baseline import normalise_line
	from baseline import report
	from baseline import resolve_baseline

CHECK = "coding-standards"

MAX_FUNCTION_LINES = 50
MAX_NESTING_LEVEL = 4
MAX_LINE_LENGTH = 200

# Names unittest calls by convention; they cannot be renamed to snake_case.
UNITTEST_HOOKS = {
	"setUp",
	"tearDown",
	"setUpClass",
	"tearDownClass",
	"setUpModule",
	"tearDownModule",
	"asyncSetUp",
	"asyncTearDown",
}

NESTED_STATEMENTS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try) + (
	(ast.TryStar,) if hasattr(ast, "TryStar") else ()
)


def handles(file_path: str) -> bool:
	return file_path.endswith(".py")


def _read(file_path: str) -> Optional[str]:
	try:
		with open(file_path, encoding="utf-8") as f:
			return f.read()
	except (UnicodeDecodeError, FileNotFoundError):
		return None


def _parse(content: Optional[str]) -> Optional[ast.Module]:
	if content is None:
		return None
	try:
		return ast.parse(content)
	except SyntaxError:
		return None


def _qualnames(tree: ast.Module) -> Dict[ast.AST, str]:
	"""Map every function and class node to its dotted qualified name."""
	names: Dict[ast.AST, str] = {}

	def visit(node: ast.AST, prefix: str) -> None:
		for child in ast.iter_child_nodes(node):
			if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
				qualname = f"{prefix}.{child.name}" if prefix else child.name
				names[child] = qualname
				visit(child, qualname)
			else:
				visit(child, prefix)

	visit(tree, "")
	return names


def _violation(file_path, rule, key, line, message, metric=None) -> Violation:
	return Violation(
		path=file_path,
		check=CHECK,
		rule=rule,
		key=key,
		line=line,
		message=message,
		metric=metric,
	)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def function_length_violations(file_path, tree, qualnames) -> List[Violation]:
	"""Functions longer than MAX_FUNCTION_LINES (def line to last body line)."""
	out = []
	for node in ast.walk(tree):
		if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(node, "end_lineno", None):
			length = node.end_lineno - node.lineno + 1
			if length > MAX_FUNCTION_LINES:
				out.append(
					_violation(
						file_path,
						"function-length",
						qualnames[node],
						node.lineno,
						f"Function '{node.name}' at line {node.lineno} is too long ({length} lines). "
						"Consider breaking it into smaller functions.",
						metric=length,
					)
				)
	return out


def naming_violations(file_path, tree, qualnames) -> List[Violation]:
	"""Functions must be snake_case, classes PascalCase (a leading _ is allowed)."""
	out = []
	for node in ast.walk(tree):
		if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
			if node.name in UNITTEST_HOOKS or node.name.startswith("_"):
				continue
			if not _is_valid_snake_case(node.name):
				out.append(
					_violation(
						file_path,
						"function-naming",
						qualnames[node],
						node.lineno,
						f"Function '{node.name}' at line {node.lineno} should use snake_case naming",
					)
				)
		elif isinstance(node, ast.ClassDef):
			if not _is_valid_pascal_case(node.name):
				out.append(
					_violation(
						file_path,
						"class-naming",
						qualnames[node],
						node.lineno,
						f"Class '{node.name}' at line {node.lineno} should use PascalCase naming",
					)
				)
	return out


def import_position_violations(file_path, tree, content) -> List[Violation]:
	"""Module-level imports that follow other module-level code.

	Imports nested in functions or classes are a deliberate technique (breaking
	an import cycle, deferring a heavy dependency) and are not checked. A
	module docstring and other bare string expressions may precede imports.
	"""
	out = []
	non_import_found = False
	for node in tree.body:
		if isinstance(node, (ast.Import, ast.ImportFrom)):
			if non_import_found:
				segment = ast.get_source_segment(content, node) or ""
				out.append(
					_violation(
						file_path,
						"import-position",
						normalise_line(segment),
						node.lineno,
						f"Line {node.lineno}: Import should be at the top of the file",
					)
				)
			continue
		if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
			continue
		non_import_found = True
	return out


def nesting_violations(file_path, tree, lines) -> List[Violation]:
	"""Control-flow statements nested deeper than MAX_NESTING_LEVEL blocks.

	Depth counts every enclosing block (class, def, if, for, with, try, ...),
	so a method body starts at level 2. An ``elif`` stays at its ``if``'s
	level. Measured on the syntax tree, so indentation inside strings or
	comments, and tabs versus spaces, do not affect it.
	"""
	out = []

	def visit(node: ast.AST, depth: int) -> None:
		for field, value in ast.iter_fields(node):
			if not isinstance(value, list):
				continue
			for child in value:
				if not isinstance(child, ast.stmt):
					# except handlers and match cases belong to their try/match;
					# their bodies sit at the same depth as the try/match body.
					if isinstance(child, ast.AST):
						visit(child, depth)
					continue
				# `elif` is an If as the sole statement of an If's orelse.
				is_elif = (
					isinstance(node, ast.If)
					and field == "orelse"
					and len(value) == 1
					and isinstance(child, ast.If)
				)
				level = depth - 1 if is_elif else depth
				if isinstance(child, NESTED_STATEMENTS) and level > MAX_NESTING_LEVEL:
					text = lines[child.lineno - 1] if child.lineno <= len(lines) else ""
					out.append(
						_violation(
							file_path,
							"nesting",
							normalise_line(text),
							child.lineno,
							f"Line {child.lineno}: Code is too deeply nested (level {level}). Consider refactoring.",
						)
					)
				visit(child, level + 1)

	visit(tree, 0)
	return out


def line_length_violations(file_path, lines) -> List[Violation]:
	out = []
	for i, line in enumerate(lines, 1):
		if len(line) > MAX_LINE_LENGTH:
			out.append(
				_violation(
					file_path,
					"line-length",
					normalise_line(line),
					i,
					f"Line {i}: Line too long ({len(line)} characters). Consider breaking into multiple lines.",
				)
			)
	return out


DEPRECATED_PATTERNS = [
	(r"\$c_obj\s*\(", "Use frappe.call() instead of $c_obj()"),
	(r"cur_frm\.set_value", "Use frm.set_value() instead of cur_frm.set_value()"),
	(r"get_query\s*\(", "Consider using frappe.db.sql() or Query Builder"),
	(r"add_fetch\s*\(", "Use frappe.db.get_value() instead of add_fetch()"),
]


def deprecated_pattern_violations(file_path, lines) -> List[Violation]:
	out = []
	for i, line in enumerate(lines, 1):
		for pattern, message in DEPRECATED_PATTERNS:
			if re.search(pattern, line):
				out.append(
					_violation(
						file_path,
						"deprecated-pattern",
						f"{pattern} :: {normalise_line(line)}",
						i,
						f"Line {i}: {message}",
					)
				)
	return out


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def collect_violations(file_path: str) -> List[Violation]:
	"""Every coding-standards violation in one file."""
	content = _read(file_path)
	if content is None:
		return []
	lines = content.split("\n")
	violations: List[Violation] = []
	tree = _parse(content)
	if tree is not None:
		qualnames = _qualnames(tree)
		violations.extend(function_length_violations(file_path, tree, qualnames))
		violations.extend(naming_violations(file_path, tree, qualnames))
		violations.extend(import_position_violations(file_path, tree, content))
		violations.extend(nesting_violations(file_path, tree, lines))
	violations.extend(line_length_violations(file_path, lines))
	violations.extend(deprecated_pattern_violations(file_path, lines))
	return violations


# Backwards-compatible helpers returning message strings, as in <= 1.0.5.


def _messages(file_path, rules):
	return [v.message for v in collect_violations(file_path) if v.rule in rules]


def check_function_length(file_path):
	return _messages(file_path, {"function-length"})


def check_naming_conventions(file_path):
	return _messages(file_path, {"function-naming", "class-naming"})


def check_import_organization(file_path):
	return _messages(file_path, {"import-position"})


def check_code_complexity(file_path):
	return _messages(file_path, {"nesting", "line-length"})


def check_frappe_specific_patterns(file_path):
	return _messages(file_path, {"deprecated-pattern"})


def _is_valid_snake_case(name):
	"""Check if name follows snake_case convention"""
	return re.match(r"^[a-z_][a-z0-9_]*$", name) is not None


def _is_valid_pascal_case(name):
	"""Check if name follows PascalCase convention.

	A leading underscore marks the name as module-private and is allowed, the
	same exemption the function check gives private functions.
	'_Resp' is a private class in PascalCase, not a naming violation.
	"""
	return re.match(r"^_?[A-Z][a-zA-Z0-9]*$", name) is not None


FOOTER = [
	"💡 Coding standards:",
	f"   ✅ Keep functions under {MAX_FUNCTION_LINES} lines",
	"   ✅ Use snake_case for functions and variables",
	"   ✅ Use PascalCase for classes",
	"   ✅ Place imports at the top of files",
	f"   ✅ Avoid deep nesting (max {MAX_NESTING_LEVEL} levels)",
	f"   ✅ Keep lines under {MAX_LINE_LENGTH} characters",
]


def main(argv: Optional[List[str]] = None) -> int:
	"""Main function to process files"""
	parser = argparse.ArgumentParser(prog="frappe-pre-commit-coding-standards")
	parser.add_argument("files", nargs="*")
	add_baseline_argument(parser)
	args = parser.parse_args(argv)
	if not args.files:
		print("Usage: check_coding_standards.py [--baseline PATH] <file1> [file2] ...")
		return 0

	violations: List[Violation] = []
	for file_path in args.files:
		if Path(file_path).exists() and handles(file_path):
			violations.extend(collect_violations(file_path))

	baseline_path = resolve_baseline(args)
	new, suppressed = apply_baseline(violations, baseline_path)
	return report(new, suppressed, baseline_path, "❌ Coding standard violations found:", FOOTER)


if __name__ == "__main__":
	sys.exit(main())
