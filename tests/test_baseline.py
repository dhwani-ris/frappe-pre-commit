"""Tests for scripts/baseline.py and the hooks' baseline integration."""

import contextlib
import io
import json
import os
import subprocess
import tempfile
import textwrap
import unittest

from scripts import baseline as bl
from scripts import check_coding_standards as cs
from scripts import check_sql_security as sql


def long_function(name, body_lines=55, indent=""):
	"""Source for a function with `body_lines` statements (too long if > 49)."""
	body = "".join(f"{indent}\tx{i} = {i}\n" for i in range(body_lines))
	return f"{indent}def {name}():\n{body}"


class TempRepo(unittest.TestCase):
	"""Each test runs in a fresh temporary directory (a git repo)."""

	def setUp(self):
		self._old_cwd = os.getcwd()
		self._tmp = tempfile.TemporaryDirectory()
		os.chdir(self._tmp.name)
		subprocess.run(["git", "init", "-q"], check=True)

	def tearDown(self):
		os.chdir(self._old_cwd)
		self._tmp.cleanup()

	def write(self, path, content):
		os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
		with open(path, "w", encoding="utf-8") as f:
			f.write(content)
		subprocess.run(["git", "add", path], check=True)

	def run_hook(self, module, *argv):
		out = io.StringIO()
		with contextlib.redirect_stdout(out):
			code = module.main(list(argv))
		return code, out.getvalue()

	def run_cli(self, *argv):
		out = io.StringIO()
		with contextlib.redirect_stdout(out):
			code = bl.main(list(argv))
		return code, out.getvalue()


class TestFingerprints(TempRepo):
	def test_line_shift_does_not_invalidate_baseline(self):
		self.write("app/mod.py", long_function("legacy"))
		self.run_cli("create")
		# Push the function down by ten lines; its key is its name, not its line.
		self.write("app/mod.py", "\n" * 10 + long_function("legacy"))
		code, out = self.run_hook(cs, "app/mod.py")
		self.assertEqual(code, 0, out)

	def test_new_long_function_is_reported(self):
		self.write("app/mod.py", long_function("legacy"))
		self.run_cli("create")
		self.write("app/mod.py", long_function("legacy") + "\n\n" + long_function("brand_new"))
		code, out = self.run_hook(cs, "app/mod.py")
		self.assertEqual(code, 1)
		self.assertIn("'brand_new'", out)
		self.assertNotIn("'legacy'", out)
		self.assertIn("1 pre-existing violation(s) accepted", out)

	def test_growing_a_baselined_function_is_reported(self):
		self.write("app/mod.py", long_function("legacy", body_lines=55))
		self.run_cli("create")
		self.write("app/mod.py", long_function("legacy", body_lines=58))
		code, out = self.run_hook(cs, "app/mod.py")
		self.assertEqual(code, 1)
		self.assertIn("baseline allows 56; it grew by 3", out)

	def test_shrinking_a_baselined_function_passes(self):
		self.write("app/mod.py", long_function("legacy", body_lines=60))
		self.run_cli("create")
		self.write("app/mod.py", long_function("legacy", body_lines=52))
		code, out = self.run_hook(cs, "app/mod.py")
		self.assertEqual(code, 0, out)

	def test_same_name_in_two_classes_are_separate_entries(self):
		src = "class A:\n" + long_function("validate", indent="\t") + "class B:\n" + long_function("validate", indent="\t")
		self.write("app/mod.py", src)
		self.run_cli("create")
		data = json.load(open(bl.DEFAULT_BASELINE))
		keys = sorted(r["key"] for r in data["files"]["app/mod.py"] if r["rule"] == "function-length")
		self.assertEqual(keys, ["A.validate", "B.validate"])

	def test_count_per_fingerprint(self):
		line = 'frappe.db.sql(f"SELECT * FROM `tab{doctype}`")\n'
		self.write("app/q.py", "import frappe\n" + line * 2)
		self.run_cli("create")
		self.write("app/q.py", "import frappe\n" + line * 3)
		code, out = self.run_hook(sql, "app/q.py")
		self.assertEqual(code, 1)
		self.assertEqual(out.count("f-strings"), 1, out)
		self.assertIn("2 pre-existing violation(s) accepted", out)

	def test_editing_a_baselined_line_makes_it_new(self):
		self.write("app/q.py", 'import frappe\nfrappe.db.sql(f"SELECT 1 FROM `tab{a}`")\n')
		self.run_cli("create")
		self.write("app/q.py", 'import frappe\nfrappe.db.sql(f"SELECT 2 FROM `tab{a}`")\n')
		code, _ = self.run_hook(sql, "app/q.py")
		self.assertEqual(code, 1)


class TestHookBaselineSelection(TempRepo):
	def test_default_baseline_is_auto_detected(self):
		self.write("app/mod.py", long_function("legacy"))
		self.assertEqual(self.run_hook(cs, "app/mod.py")[0], 1)
		self.run_cli("create")
		self.assertEqual(self.run_hook(cs, "app/mod.py")[0], 0)

	def test_no_baseline_flag_reports_everything(self):
		self.write("app/mod.py", long_function("legacy"))
		self.run_cli("create")
		self.assertEqual(self.run_hook(cs, "--no-baseline", "app/mod.py")[0], 1)

	def test_explicit_baseline_path(self):
		self.write("app/mod.py", long_function("legacy"))
		self.run_cli("--baseline", "custom.json", "create")
		self.assertFalse(os.path.exists(bl.DEFAULT_BASELINE))
		self.assertEqual(self.run_hook(cs, "app/mod.py")[0], 1)
		self.assertEqual(self.run_hook(cs, "--baseline", "custom.json", "app/mod.py")[0], 0)

	def test_dot_slash_paths_match(self):
		self.write("app/mod.py", long_function("legacy"))
		self.run_cli("create")
		self.assertEqual(self.run_hook(cs, "./app/mod.py")[0], 0)

	def test_invalid_baseline_file_is_rejected(self):
		self.write("app/mod.py", long_function("legacy"))
		with open(bl.DEFAULT_BASELINE, "w") as f:
			json.dump({"something": "else"}, f)
		with self.assertRaises(ValueError):
			self.run_hook(cs, "app/mod.py")


class TestCli(TempRepo):
	def test_create_writes_deterministic_sorted_file(self):
		self.write("b.py", long_function("two"))
		self.write("a.py", long_function("one"))
		self.run_cli("create")
		first = open(bl.DEFAULT_BASELINE).read()
		self.run_cli("create")
		self.assertEqual(first, open(bl.DEFAULT_BASELINE).read())
		self.assertEqual(list(json.loads(first)["files"]), ["a.py", "b.py"])

	def test_prune_removes_fixed_and_never_adds(self):
		self.write("a.py", long_function("one") + "\n\n" + long_function("two"))
		self.run_cli("create")
		# Fix `one`, and introduce a brand-new violation `three`.
		self.write("a.py", "def one():\n\tpass\n\n\n" + long_function("two") + "\n\n" + long_function("three"))
		code, out = self.run_cli("prune")
		self.assertEqual(code, 0)
		self.assertIn("Pruned 1", out)
		keys = [r["key"] for r in json.load(open(bl.DEFAULT_BASELINE))["files"]["a.py"]]
		self.assertEqual(keys, ["two"])

	def test_prune_lowers_the_ratchet(self):
		self.write("a.py", long_function("one", body_lines=60))
		self.run_cli("create")
		self.write("a.py", long_function("one", body_lines=53))
		self.run_cli("prune")
		row = json.load(open(bl.DEFAULT_BASELINE))["files"]["a.py"][0]
		self.assertEqual(row["max"], 54)
		# Growing back past the new ceiling now fails.
		self.write("a.py", long_function("one", body_lines=57))
		self.assertEqual(self.run_hook(cs, "a.py")[0], 1)

	def test_partial_create_keeps_other_files(self):
		self.write("a.py", long_function("one"))
		self.write("b.py", long_function("two"))
		self.run_cli("create")
		self.write("b.py", "def two():\n\tpass\n")
		self.run_cli("create", "b.py")
		files = json.load(open(bl.DEFAULT_BASELINE))["files"]
		self.assertIn("a.py", files)
		self.assertNotIn("b.py", files)

	def test_partial_prune_keeps_unscanned_files(self):
		self.write("a.py", long_function("one"))
		self.write("b.py", long_function("two"))
		self.run_cli("create")
		self.run_cli("prune", "b.py")
		self.assertEqual(sorted(json.load(open(bl.DEFAULT_BASELINE))["files"]), ["a.py", "b.py"])

	def test_check_scope_keeps_other_checks(self):
		self.write("a.py", "import frappe\n" + 'frappe.db.sql(f"SELECT 1 FROM `tab{x}`")\n' + long_function("one"))
		self.run_cli("create")
		self.run_cli("--check", "coding-standards", "create")
		checks = {r["check"] for r in json.load(open(bl.DEFAULT_BASELINE))["files"]["a.py"]}
		self.assertEqual(checks, {"coding-standards", "sql-security"})

	def test_summary(self):
		self.write("a.py", long_function("one"))
		self.run_cli("create")
		code, out = self.run_cli("summary")
		self.assertEqual(code, 0)
		self.assertIn("coding-standards / function-length", out)

	def test_summary_without_baseline(self):
		code, out = self.run_cli("summary")
		self.assertEqual(code, 1)
		self.assertIn("not found", out)


class TestBaselineUnit(unittest.TestCase):
	def test_normalise_path(self):
		self.assertEqual(bl.normalise_path("./a/b.py"), "a/b.py")
		self.assertEqual(bl.normalise_path("a/b.py"), "a/b.py")

	def test_normalise_line(self):
		self.assertEqual(bl.normalise_line("\t\tx  =   1 "), "x = 1")

	def test_filter_orders_suppression_by_line(self):
		v = [
			bl.Violation("a.py", "c", "r", "k", line=9, message="late"),
			bl.Violation("a.py", "c", "r", "k", line=1, message="early"),
		]
		base = bl.Baseline({"a.py": [{"check": "c", "rule": "r", "key": "k", "count": 1}]})
		new, suppressed = base.filter(v)
		self.assertEqual(suppressed, 1)
		self.assertEqual([x.message for x in new], ["late"])


if __name__ == "__main__":
	unittest.main()
