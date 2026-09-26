"""Tests for the individual checkers, including the 1.0.6 false-positive fixes."""

import os
import tempfile
import textwrap
import unittest

from scripts import check_coding_standards as cs
from scripts import check_doctype_naming as dn
from scripts import check_sql_security as sql


class FileCase(unittest.TestCase):
	def setUp(self):
		self._tmp = tempfile.TemporaryDirectory()

	def tearDown(self):
		self._tmp.cleanup()

	def file(self, name, content):
		path = os.path.join(self._tmp.name, name)
		with open(path, "w", encoding="utf-8") as f:
			f.write(textwrap.dedent(content))
		return path

	def rules(self, module, path):
		return [(v.rule, v.key) for v in module.collect_violations(path)]


class TestCodingStandards(FileCase):
	def test_unittest_hook_names_are_not_naming_violations(self):
		path = self.file(
			"test_x.py",
			"""
			import unittest

			def setUpModule():
				pass

			class TestX(unittest.TestCase):
				@classmethod
				def setUpClass(cls):
					pass

				@classmethod
				def tearDownClass(cls):
					pass

				def test_Mixed_Case(self):
					pass
			""",
		)
		naming = [k for r, k in self.rules(cs, path) if r == "function-naming"]
		self.assertEqual(naming, ["TestX.test_Mixed_Case"])

	def test_private_class_is_valid_pascal_case(self):
		path = self.file("m.py", "class _Resp:\n\tpass\n\nclass lower_case:\n\tpass\n")
		self.assertEqual([k for r, k in self.rules(cs, path) if r == "class-naming"], ["lower_case"])

	def test_indentation_inside_strings_is_not_nesting(self):
		# A docstring and an SQL string with deep indentation, but shallow code.
		path = self.file(
			"m.py",
			'''
			def f():
				"""
				                      if this were code it would be deep
				"""
				sql = """
				                      SELECT 1 -- if deep
				"""
				return sql
			''',
		)
		self.assertEqual([r for r, _ in self.rules(cs, path) if r == "nesting"], [])

	def test_real_deep_nesting_is_reported_once_per_statement(self):
		path = self.file(
			"m.py",
			"""
			class A:
				def f(self, x):
					for a in x:
						for b in a:
							if b:
								while b:
									b -= 1
			""",
		)
		nesting = [v for v in cs.collect_violations(path) if v.rule == "nesting"]
		# class(0) > def(1) > for(2) > for(3) > if(4) > while(5): only the while.
		self.assertEqual(len(nesting), 1)
		self.assertIn("level 5", nesting[0].message)

	def test_elif_chain_does_not_increase_depth(self):
		body = "".join(f"\telif x == {i}:\n\t\tpass\n" for i in range(1, 10))
		path = self.file("m.py", "def f(x):\n\tif x == 0:\n\t\tpass\n" + body)
		self.assertEqual([r for r, _ in self.rules(cs, path) if r == "nesting"], [])

	def test_except_body_depth(self):
		path = self.file(
			"m.py",
			"""
			def f():
				for a in b:
					try:
						pass
					except Exception:
						if a:
							pass
			""",
		)
		# def(0) body at 1: for(1) > try(2) > except body(3): if at level 3 -> fine.
		self.assertEqual([r for r, _ in self.rules(cs, path) if r == "nesting"], [])

	def test_import_rules(self):
		path = self.file(
			"m.py",
			'''
			"""Module docstring."""
			import os

			X = 1

			import re

			def f():
				import json
			''',
		)
		imports = [k for r, k in self.rules(cs, path) if r == "import-position"]
		self.assertEqual(imports, ["import re"])

	def test_function_length_metric(self):
		path = self.file("m.py", "def f():\n" + "\tx = 1\n" * 60)
		(v,) = [v for v in cs.collect_violations(path) if v.rule == "function-length"]
		self.assertEqual((v.key, v.metric), ("f", 61))

	def test_long_line(self):
		path = self.file("m.py", "x = '" + "a" * 250 + "'\n")
		self.assertEqual([r for r, _ in self.rules(cs, path)], ["line-length"])

	def test_syntax_error_file_is_skipped_for_ast_rules(self):
		path = self.file("m.py", "def f(:\n")
		self.assertEqual(cs.collect_violations(path), [])

	def test_legacy_helpers_still_return_messages(self):
		path = self.file("m.py", "def f():\n" + "\tx = 1\n" * 60)
		self.assertTrue(cs.check_function_length(path)[0].startswith("Function 'f' at line 1 is too long"))


class TestDoctypeNaming(unittest.TestCase):
	def test_labels_that_are_now_valid(self):
		for label in [
			"Season ID",
			"CFPP Push Status",
			"LGD State Code",
			"Report PDF",
			"SHA-256",
			"Raw GET Response",
			"DO Details (read-only)",
			"Active (Per CFPP)",
			"Throughput (editable while running)",
			"Seek Calls per Minute",
			"Resolved to a Farmer",
			"Area of Address",
			"Discount %",
			"Address 1",
			"A & B",
		]:
			with self.subTest(label=label):
				self.assertTrue(dn._is_valid_field_label(label))

	def test_labels_that_are_still_invalid(self):
		for label in ["season ID", "Season id", "Season_ID", "customer name", "Name of the customer"]:
			with self.subTest(label=label):
				self.assertFalse(dn._is_valid_field_label(label))

	def test_fieldnames(self):
		self.assertTrue(dn._is_valid_field_name("_source_doctype"))
		self.assertTrue(dn._is_valid_field_name("customer_name"))
		self.assertFalse(dn._is_valid_field_name("CustomerName"))
		self.assertFalse(dn._is_valid_field_name("__dunder"))

	def test_wildcard_form_handler_is_not_a_doctype(self):
		with tempfile.TemporaryDirectory() as d:
			path = os.path.join(d, "x.js")
			with open(path, "w") as f:
				f.write('frappe.ui.form.on("*", {});\nfrappe.ui.form.on("sales_order", {});\n')
			keys = [v.key.split(" :: ")[0] for v in dn.collect_violations(path)]
			self.assertEqual(keys, ["sales_order"])

	def test_doctype_json(self):
		with tempfile.TemporaryDirectory() as d:
			path = os.path.join(d, "x.json")
			with open(path, "w") as f:
				f.write(
					'{"doctype": "DocType", "name": "Sales Order", "fields": ['
					'{"fieldname": "season_id", "label": "Season ID"},'
					'{"fieldname": "bad", "label": "bad label"}]}'
				)
			self.assertEqual(
				[(v.rule, v.key) for v in dn.collect_violations(path)],
				[("field-label", "bad: bad label")],
			)

	def test_non_doctype_json_is_ignored(self):
		with tempfile.TemporaryDirectory() as d:
			path = os.path.join(d, "x.json")
			with open(path, "w") as f:
				f.write('{"format": 1, "files": {}}')
			self.assertEqual(dn.collect_violations(path), [])


class TestSqlSecurity(FileCase):
	def test_patterns(self):
		path = self.file(
			"q.py",
			"""
			import frappe
			frappe.db.sql(f"SELECT * FROM `tab{dt}`")
			frappe.db.sql("SELECT * FROM tabUser WHERE name = %s", name)
			# frappe.db.sql(f"commented out")
			frappe.db.set_value("User", u, "api_key", "abc123")
			""",
		)
		rules = [r for r, _ in self.rules(sql, path)]
		self.assertEqual(rules, ["sql-injection", "unencrypted-secret"])

	def test_legacy_helper(self):
		path = self.file("q.py", 'import frappe\nfrappe.db.sql(f"SELECT 1")\n')
		self.assertEqual(
			sql.check_sql_injection_patterns(path),
			["Line 2: SQL query using f-strings - use parameterized queries with %s"],
		)


if __name__ == "__main__":
	unittest.main()
