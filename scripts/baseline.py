#!/usr/bin/env python3
"""
Baseline support for the frappe-pre-commit hooks.

A baseline lets a project adopt these hooks without first fixing every
existing violation. The violations that exist when the baseline is created
are recorded in ``.frappe-pre-commit-baseline.json``; afterwards the hooks
report only violations that are NOT in the baseline, so new code is held to
the standard while legacy code is left alone until someone touches it.

Each violation is fingerprinted by ``(file, check, rule, key)``. The key never
contains a line number (it is a qualified function name, an import statement,
a field name, or the normalised text of the offending line), so adding or
removing lines elsewhere in a file does not invalidate the baseline.

Rules that carry a measurement (function length) are ratcheted: a baselined
function passes only while it is no longer than its recorded length, so a
legacy long function cannot silently keep growing.

Usage::

    frappe-pre-commit-baseline create     # snapshot current violations
    frappe-pre-commit-baseline prune      # drop entries that are now fixed
    frappe-pre-commit-baseline summary    # counts per check and rule
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

DEFAULT_BASELINE = ".frappe-pre-commit-baseline.json"
BASELINE_FORMAT = 1


@dataclass
class Violation:
	"""One finding from a checker.

	``message`` is what the hook prints; ``key`` identifies the violation
	independently of its line number; ``metric`` is an optional measurement
	(e.g. function length) that the baseline ratchets on.
	"""

	path: str
	check: str
	rule: str
	key: str
	line: int
	message: str
	metric: Optional[int] = None

	def display(self) -> str:
		return f"{self.path}: {self.message}"


def normalise_path(path: str) -> str:
	"""Return a stable, repo-relative POSIX path for use as a baseline key."""
	p = Path(path)
	if p.is_absolute():
		try:
			p = p.resolve().relative_to(Path.cwd().resolve())
		except ValueError:
			pass
	posix = p.as_posix()
	while posix.startswith("./"):
		posix = posix[2:]
	return posix


def normalise_line(text: str) -> str:
	"""Collapse whitespace so re-indenting a line does not change its key."""
	return " ".join(text.split())


# ---------------------------------------------------------------------------
# Baseline file I/O
# ---------------------------------------------------------------------------


class Baseline:
	"""In-memory baseline: allowed count and max metric per fingerprint."""

	def __init__(self, entries: Optional[Dict[str, List[dict]]] = None):
		# path -> list of {"check", "rule", "key", "count", ["max"]}
		self.entries: Dict[str, List[dict]] = entries or {}

	# -- persistence ---------------------------------------------------------

	@classmethod
	def load(cls, path: str) -> "Baseline":
		with open(path, encoding="utf-8") as f:
			data = json.load(f)
		if not isinstance(data, dict) or data.get("format") != BASELINE_FORMAT:
			raise ValueError(
				f"{path} is not a frappe-pre-commit baseline (expected format {BASELINE_FORMAT})"
			)
		return cls(data.get("files") or {})

	def save(self, path: str) -> None:
		files = {}
		for file_path in sorted(self.entries):
			rows = sorted(
				self.entries[file_path], key=lambda r: (r["check"], r["rule"], r["key"])
			)
			if rows:
				files[file_path] = rows
		data = {
			"format": BASELINE_FORMAT,
			"description": (
				"Pre-existing violations accepted by frappe-pre-commit. "
				"Regenerate with `frappe-pre-commit-baseline create`; "
				"shrink with `frappe-pre-commit-baseline prune`."
			),
			"files": files,
		}
		with open(path, "w", encoding="utf-8") as f:
			json.dump(data, f, indent=1, ensure_ascii=False, sort_keys=False)
			f.write("\n")

	# -- building ------------------------------------------------------------

	@classmethod
	def from_violations(cls, violations: Iterable[Violation]) -> "Baseline":
		grouped: Dict[Tuple[str, str, str, str], List[Violation]] = defaultdict(list)
		for v in violations:
			grouped[(normalise_path(v.path), v.check, v.rule, v.key)].append(v)
		entries: Dict[str, List[dict]] = defaultdict(list)
		for (path, check, rule, key), items in grouped.items():
			row = {"check": check, "rule": rule, "key": key, "count": len(items)}
			metrics = [i.metric for i in items if i.metric is not None]
			if metrics:
				row["max"] = max(metrics)
			entries[path].append(row)
		return cls(dict(entries))

	def _index(self) -> Dict[Tuple[str, str, str, str], dict]:
		return {
			(path, row["check"], row["rule"], row["key"]): row
			for path, rows in self.entries.items()
			for row in rows
		}

	# -- matching ------------------------------------------------------------

	def filter(self, violations: Iterable[Violation]) -> Tuple[List[Violation], int]:
		"""Split violations into (new, suppressed_count).

		For each fingerprint the first ``count`` occurrences (in line order)
		are grandfathered; any beyond that are new. An occurrence whose metric
		exceeds the recorded ``max`` is always new, with a message saying how
		far it grew.
		"""
		index = self._index()
		grouped: Dict[Tuple[str, str, str, str], List[Violation]] = defaultdict(list)
		for v in violations:
			grouped[(normalise_path(v.path), v.check, v.rule, v.key)].append(v)

		new: List[Violation] = []
		suppressed = 0
		for fingerprint, items in grouped.items():
			row = index.get(fingerprint)
			if row is None:
				new.extend(items)
				continue
			allowed = int(row.get("count", 0))
			ceiling = row.get("max")
			for item in sorted(items, key=lambda i: i.line):
				if ceiling is not None and item.metric is not None and item.metric > ceiling:
					item.message = f"{item.message} (baseline allows {ceiling}; it grew by {item.metric - ceiling})"
					new.append(item)
				elif allowed > 0:
					allowed -= 1
					suppressed += 1
				else:
					new.append(item)
		new.sort(key=lambda v: (normalise_path(v.path), v.line))
		return new, suppressed

	def prune(
		self,
		violations: Iterable[Violation],
		checks: Iterable[str],
		paths: Optional[Iterable[str]] = None,
	) -> int:
		"""Shrink the baseline to what still occurs; never add entries.

		Only entries inside the scanned scope (``checks``, and ``paths`` when
		given) are considered, so a partial scan never drops entries it did
		not look at. Returns the number of violations removed.
		"""
		checks = set(checks)
		scope = None if paths is None else {normalise_path(p) for p in paths}
		current = Baseline.from_violations(violations)._index()
		removed = 0
		for path in list(self.entries):
			if scope is not None and path not in scope:
				continue
			kept = []
			for row in self.entries[path]:
				if row["check"] not in checks:
					kept.append(row)
					continue
				now = current.get((path, row["check"], row["rule"], row["key"]))
				if now is None:
					removed += row["count"]
					continue
				new_count = min(row["count"], now["count"])
				removed += row["count"] - new_count
				row = dict(row, count=new_count)
				if "max" in row and "max" in now:
					row["max"] = min(row["max"], now["max"])
				kept.append(row)
			if kept:
				self.entries[path] = kept
			else:
				del self.entries[path]
		return removed

	def replace_scope(
		self, other: "Baseline", checks: Iterable[str], paths: Optional[Iterable[str]] = None
	) -> None:
		"""Replace this baseline's entries inside the scope with ``other``'s."""
		checks = set(checks)
		scope = None if paths is None else {normalise_path(p) for p in paths}
		for path in list(self.entries):
			if scope is not None and path not in scope:
				continue
			kept = [r for r in self.entries[path] if r["check"] not in checks]
			if kept:
				self.entries[path] = kept
			else:
				del self.entries[path]
		for path, rows in other.entries.items():
			self.entries.setdefault(path, []).extend(rows)

	def counts(self) -> Dict[Tuple[str, str], int]:
		out: Dict[Tuple[str, str], int] = defaultdict(int)
		for rows in self.entries.values():
			for row in rows:
				out[(row["check"], row["rule"])] += row["count"]
		return dict(out)


# ---------------------------------------------------------------------------
# Hook-side helpers
# ---------------------------------------------------------------------------


def add_baseline_argument(parser: argparse.ArgumentParser) -> None:
	parser.add_argument(
		"--baseline",
		metavar="PATH",
		default=None,
		help=(
			"Baseline of accepted pre-existing violations. Defaults to "
			f"{DEFAULT_BASELINE} in the current directory when that file exists."
		),
	)
	parser.add_argument(
		"--no-baseline",
		action="store_true",
		help="Ignore any baseline and report every violation.",
	)


def resolve_baseline(args: argparse.Namespace) -> Optional[str]:
	if getattr(args, "no_baseline", False):
		return None
	if args.baseline:
		return args.baseline
	return DEFAULT_BASELINE if os.path.isfile(DEFAULT_BASELINE) else None


def apply_baseline(
	violations: List[Violation], baseline_path: Optional[str]
) -> Tuple[List[Violation], int]:
	"""Return (violations to report, number suppressed by the baseline)."""
	if not baseline_path:
		return violations, 0
	baseline = Baseline.load(baseline_path)
	return baseline.filter(violations)


def report(
	violations: List[Violation],
	suppressed: int,
	baseline_path: Optional[str],
	header: str,
	footer: Iterable[str],
) -> int:
	"""Print the hook's output and return its exit code."""
	if violations:
		print(header)
		for v in violations:
			print(f"  {v.display()}")
		if suppressed:
			print(f"\nℹ️  {suppressed} pre-existing violation(s) accepted by {baseline_path}.")
		print()
		for line in footer:
			print(line)
		return 1
	return 0


# ---------------------------------------------------------------------------
# CLI: frappe-pre-commit-baseline
# ---------------------------------------------------------------------------


def _checkers():
	# Imported lazily so each hook stays importable on its own.
	try:
		from scripts import check_coding_standards, check_doctype_naming, check_sql_security
	except ImportError:  # run directly as `python scripts/baseline.py`
		import check_coding_standards
		import check_doctype_naming
		import check_sql_security

	return {
		check_coding_standards.CHECK: check_coding_standards,
		check_sql_security.CHECK: check_sql_security,
		check_doctype_naming.CHECK: check_doctype_naming,
	}


def _git_files() -> List[str]:
	try:
		out = subprocess.run(
			["git", "ls-files", "-z"], check=True, capture_output=True, text=True
		).stdout
	except (OSError, subprocess.CalledProcessError):
		sys.exit("frappe-pre-commit-baseline: run inside a git repository, or pass file paths.")
	return [p for p in out.split("\0") if p]


def collect(checks: Iterable[str], files: Optional[List[str]] = None) -> List[Violation]:
	"""Run the given checks over ``files`` (default: every file git tracks)."""
	files = files or _git_files()
	registry = _checkers()
	violations: List[Violation] = []
	for check in checks:
		module = registry[check]
		for path in files:
			if module.handles(path) and os.path.isfile(path):
				violations.extend(module.collect_violations(path))
	return violations


def main(argv: Optional[List[str]] = None) -> int:
	registry_names = ["coding-standards", "sql-security", "doctype-naming"]
	parser = argparse.ArgumentParser(
		prog="frappe-pre-commit-baseline",
		description="Create or maintain the baseline of accepted pre-existing violations.",
	)
	parser.add_argument("--baseline", default=DEFAULT_BASELINE, metavar="PATH")
	parser.add_argument(
		"--check",
		action="append",
		choices=registry_names,
		help="Limit to one check (repeatable). Default: all checks.",
	)
	sub = parser.add_subparsers(dest="command", required=True)
	create = sub.add_parser("create", help="Snapshot every current violation.")
	create.add_argument("files", nargs="*", help="Files to scan (default: git ls-files).")
	prune = sub.add_parser("prune", help="Remove entries that no longer occur. Never adds.")
	prune.add_argument("files", nargs="*", help="Files to scan (default: git ls-files).")
	sub.add_parser("summary", help="Print the number of accepted violations per rule.")
	args = parser.parse_args(argv)
	checks = args.check or registry_names

	# A partial scan (some checks, or explicit files) only rewrites that scope.
	scope_paths = getattr(args, "files", None) or None
	partial = bool(args.check or scope_paths)

	if args.command == "create":
		violations = collect(checks, args.files)
		fresh = Baseline.from_violations(violations)
		if partial and os.path.isfile(args.baseline):
			baseline = Baseline.load(args.baseline)
			baseline.replace_scope(fresh, checks, scope_paths)
		else:
			baseline = fresh
		baseline.save(args.baseline)
		print(f"Wrote {args.baseline}: {len(violations)} violation(s) recorded in this scan.")
		_print_counts(baseline)
		return 0

	if not os.path.isfile(args.baseline):
		print(f"{args.baseline} not found. Run `frappe-pre-commit-baseline create` first.")
		return 1
	baseline = Baseline.load(args.baseline)

	if args.command == "prune":
		removed = baseline.prune(collect(checks, args.files), checks, scope_paths)
		baseline.save(args.baseline)
		print(f"Pruned {removed} fixed violation(s) from {args.baseline}.")
		_print_counts(baseline)
		return 0

	_print_counts(baseline)
	return 0


def _print_counts(baseline: Baseline) -> None:
	counts = baseline.counts()
	if not counts:
		print("Baseline is empty.")
		return
	width = max(len(f"{c} / {r}") for c, r in counts)
	for (check, rule), n in sorted(counts.items()):
		print(f"  {check + ' / ' + rule:<{width}}  {n}")
	print(f"  {'total':<{width}}  {sum(counts.values())}")


if __name__ == "__main__":
	sys.exit(main())
