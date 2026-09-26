#!/usr/bin/env python3
"""
DocType Naming Convention Checker for Frappe Framework

This script checks for proper DocType naming conventions and field naming.

Existing violations can be accepted through a baseline file; see
scripts/baseline.py and the README section "Adopting on an existing codebase".
"""

from __future__ import annotations

import argparse
import json
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
except ImportError:  # run directly as `python scripts/check_doctype_naming.py`
	from baseline import Violation
	from baseline import add_baseline_argument
	from baseline import apply_baseline
	from baseline import normalise_line
	from baseline import report
	from baseline import resolve_baseline

CHECK = "doctype-naming"

# frappe.ui.form.on("*", ...) registers a handler for every DocType.
WILDCARD_DOCTYPE = "*"

# Words that stay lowercase in Title Case when they are not the first word.
MINOR_WORDS = {
	# prepositions
	"of", "in", "at", "to", "for", "with", "by", "from", "on", "up", "down",
	"out", "off", "over", "under", "per", "via", "into", "onto", "vs",
	# articles and conjunctions
	"a", "an", "the", "and", "or", "nor", "but", "as",
}  # fmt: skip


def handles(file_path: str) -> bool:
	return file_path.endswith((".py", ".js", ".json"))


def _violation(file_path, rule, key, line, message) -> Violation:
	return Violation(path=file_path, check=CHECK, rule=rule, key=key, line=line, message=message)


def json_violations(file_path: str) -> List[Violation]:
	"""DocType JSON: DocType name, fieldnames and field labels."""
	try:
		with open(file_path, encoding="utf-8") as f:
			doctype_data = json.load(f)
	except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError):
		return []

	# Check if it's a DocType JSON file
	if not isinstance(doctype_data, dict) or doctype_data.get("doctype") != "DocType":
		return []

	out = []
	doctype_name = doctype_data.get("name", "")
	if not _is_valid_doctype_name(doctype_name):
		out.append(
			_violation(
				file_path,
				"doctype-name",
				doctype_name,
				0,
				f"DocType name '{doctype_name}' should use Title Case with spaces (e.g., 'Sales Order')",
			)
		)

	for field in doctype_data.get("fields", []):
		if not isinstance(field, dict):
			continue
		fieldname = field.get("fieldname", "")
		label = field.get("label", "")
		if fieldname and not _is_valid_field_name(fieldname):
			out.append(
				_violation(
					file_path,
					"field-name",
					fieldname,
					0,
					f"Field '{fieldname}' should use snake_case naming",
				)
			)
		if label and not _is_valid_field_label(label):
			out.append(
				_violation(
					file_path,
					"field-label",
					f"{fieldname}: {label}",
					0,
					f"Field label '{label}' should use Title Case",
				)
			)
	return out


PY_PATTERNS = [
	r'frappe\.get_doc\s*\(\s*["\']([^"\']+)["\']',
	r'frappe\.new_doc\s*\(\s*["\']([^"\']+)["\']',
	r'frappe\.db\.get_value\s*\(\s*["\']([^"\']+)["\']',
	r'frappe\.db\.set_value\s*\(\s*["\']([^"\']+)["\']',
]

JS_PATTERNS = [
	r'frappe\.ui\.form\.on\s*\(\s*["\']([^"\']+)["\']',
	r'frappe\.db\.get_value\s*\(\s*["\']([^"\']+)["\']',
	r'frappe\.new_doc\s*\(\s*["\']([^"\']+)["\']',
]


def _reference_violations(file_path, patterns, comment_prefixes, allow_tab_prefix) -> List[Violation]:
	try:
		with open(file_path, encoding="utf-8") as f:
			lines = f.read().split("\n")
	except (UnicodeDecodeError, FileNotFoundError):
		return []
	out = []
	for i, line in enumerate(lines, 1):
		if line.strip().startswith(comment_prefixes):
			continue
		for pattern in patterns:
			for match in re.finditer(pattern, line):
				doctype_name = match.group(1)
				if doctype_name == WILDCARD_DOCTYPE:
					continue
				if allow_tab_prefix and doctype_name.startswith("tab"):
					continue
				if not _is_valid_doctype_name(doctype_name):
					out.append(
						_violation(
							file_path,
							"doctype-reference",
							f"{doctype_name} :: {normalise_line(line)}",
							i,
							f"Line {i}: DocType '{doctype_name}' should use Title Case with spaces",
						)
					)
	return out


def collect_violations(file_path: str) -> List[Violation]:
	"""Every DocType-naming violation in one file."""
	if file_path.endswith(".json"):
		return json_violations(file_path)
	if file_path.endswith(".py"):
		return _reference_violations(file_path, PY_PATTERNS, ("#",), allow_tab_prefix=True)
	if file_path.endswith(".js"):
		return _reference_violations(file_path, JS_PATTERNS, ("//", "/*"), allow_tab_prefix=False)
	return []


# Backwards-compatible helpers returning message strings, as in <= 1.0.5.


def check_doctype_json_file(file_path):
	return [v.message for v in json_violations(file_path)]


def check_python_doctype_usage(file_path):
	return [v.message for v in _reference_violations(file_path, PY_PATTERNS, ("#",), True)]


def check_javascript_doctype_usage(file_path):
	return [v.message for v in _reference_violations(file_path, JS_PATTERNS, ("//", "/*"), False)]


def _is_valid_doctype_name(name):
	"""Check if DocType name follows Title Case with Spaces convention"""
	if not name:
		return False

	# Should be Title Case with spaces, no underscores or hyphens
	# Examples: "Sales Order", "Item Price", "User"
	return re.match(r"^[A-Z][a-zA-Z\s]*$", name) is not None and "_" not in name and "-" not in name


def _is_valid_field_name(fieldname):
	"""Check if field name follows snake_case convention.

	A single leading underscore is allowed: Frappe itself uses it for
	internal columns such as ``_user_tags`` and ``_comments``.
	"""
	if not fieldname:
		return False

	# Should be snake_case (lowercase with underscores)
	# Examples: "customer_name", "item_code", "posting_date", "_source_doctype"
	return re.match(r"^_?[a-z][a-z0-9_]*$", fieldname) is not None


def _is_acronym(word):
	"""'ID', 'CFPP', 'SHA-256', 'UOM', 'KYC/eKYC'-style all-caps tokens."""
	letters = [c for c in word if c.isalpha()]
	return len(letters) >= 2 and all(c.isupper() for c in letters)


def _is_valid_field_label(label):
	"""Check if field label follows Title Case convention.

	Allowed:
	- Numbers (e.g., "Address 1", "Address 2")
	- Special characters like "&", "%", "(", ")", "-" (e.g., "A & B", "Discount %")
	- Minor words in lowercase after the first word ("Area of Address", "Calls per Minute")
	- Abbreviations and acronyms ("Season ID", "CFPP Push Status", "Report PDF")
	- Any casing inside parentheses, which holds a note rather than the title
	  ("Details (read-only)", "Active (Per CFPP)")
	"""
	if not label or not label.strip():
		return False

	# Parenthesised notes are free text; drop them before checking the title.
	title = re.sub(r"\([^()]*\)", " ", label)
	words = title.split()

	for i, word in enumerate(words):
		# Skip validation for numbers and standalone special characters
		if word.isdigit() or all(not c.isalnum() for c in word):
			continue

		if "_" in word:  # No underscores allowed
			return False

		if _is_acronym(word):
			continue

		# Allow lowercase for minor words (except at the beginning)
		if i > 0 and word.lower() in MINOR_WORDS:
			continue

		# For all other words, first letter should be uppercase
		first_alpha = next((c for c in word if c.isalpha()), None)
		if first_alpha is not None and not first_alpha.isupper():
			return False

	return True


FOOTER = [
	"💡 DocType naming conventions:",
	"   ✅ DocType names: Title Case with spaces ('Sales Order', 'Item Price')",
	"   ✅ Field names: snake_case ('customer_name', 'item_code')",
	"   ✅ Field labels: Title Case ('Customer Name', 'Item Code', 'Season ID')",
	"   ✅ Method names: snake_case ('validate_customer_details')",
]


def main(argv: Optional[List[str]] = None) -> int:
	"""Main function to process files"""
	parser = argparse.ArgumentParser(prog="frappe-pre-commit-doctype-naming")
	parser.add_argument("files", nargs="*")
	add_baseline_argument(parser)
	args = parser.parse_args(argv)
	if not args.files:
		print("Usage: check_doctype_naming.py [--baseline PATH] <file1> [file2] ...")
		return 0

	violations: List[Violation] = []
	for file_path in args.files:
		if Path(file_path).exists() and handles(file_path):
			violations.extend(collect_violations(file_path))

	baseline_path = resolve_baseline(args)
	new, suppressed = apply_baseline(violations, baseline_path)
	return report(new, suppressed, baseline_path, "❌ DocType naming convention violations found:", FOOTER)


if __name__ == "__main__":
	sys.exit(main())
