"""Regression tests for scripts/check_coding_standards.py."""

import textwrap

from scripts.check_coding_standards import (
	check_import_organization,
	check_naming_conventions,
	_is_valid_pascal_case,
	_is_valid_snake_case,
)


def _write(tmp_path, filename, source):
	path = tmp_path / filename
	path.write_text(textwrap.dedent(source))
	return str(path)


class TestNamingConventionsUnittestLifecycle:
	"""setUp/tearDown/setUpClass/... are unittest-mandated names and must
	never be flagged for snake_case in a test_*.py file."""

	def test_set_up_and_tear_down_are_exempt(self, tmp_path):
		file_path = _write(
			tmp_path,
			"test_example.py",
			"""
			class TestThing:
				def setUp(self):
					pass

				def tearDown(self):
					pass
			""",
		)
		assert check_naming_conventions(file_path) == []

	def test_set_up_class_and_tear_down_class_are_exempt(self, tmp_path):
		file_path = _write(
			tmp_path,
			"test_example.py",
			"""
			class TestThing:
				@classmethod
				def setUpClass(cls):
					pass

				@classmethod
				def tearDownClass(cls):
					pass
			""",
		)
		assert check_naming_conventions(file_path) == []

	def test_set_up_module_and_tear_down_module_are_exempt(self, tmp_path):
		file_path = _write(
			tmp_path,
			"test_example.py",
			"""
			def setUpModule():
				pass

			def tearDownModule():
				pass
			""",
		)
		assert check_naming_conventions(file_path) == []

	def test_lifecycle_names_are_not_exempt_outside_test_files(self, tmp_path):
		"""The exemption is scoped to test_*.py files; the same camelCase name
		in a regular module is still a real violation."""
		file_path = _write(
			tmp_path,
			"example.py",
			"""
			class Thing:
				def setUpClass(cls):
					pass
			""",
		)
		errors = check_naming_conventions(file_path)
		assert len(errors) == 1
		assert "setUpClass" in errors[0]

	def test_other_camel_case_methods_still_flagged_in_test_files(self, tmp_path):
		file_path = _write(
			tmp_path,
			"test_example.py",
			"""
			class TestThing:
				def someHelperMethod(self):
					pass
			""",
		)
		errors = check_naming_conventions(file_path)
		assert len(errors) == 1
		assert "someHelperMethod" in errors[0]


class TestNamingConventionsGeneral:
	def test_private_functions_are_exempt(self, tmp_path):
		file_path = _write(
			tmp_path,
			"example.py",
			"""
			def _validate_program_access_duplicates():
				pass
			""",
		)
		assert check_naming_conventions(file_path) == []

	def test_valid_pascal_case_class_passes(self, tmp_path):
		file_path = _write(
			tmp_path,
			"example.py",
			"""
			class UserManager:
				pass
			""",
		)
		assert check_naming_conventions(file_path) == []

	def test_invalid_class_name_flagged(self, tmp_path):
		file_path = _write(
			tmp_path,
			"example.py",
			"""
			class userManager:
				pass
			""",
		)
		errors = check_naming_conventions(file_path)
		assert len(errors) == 1
		assert "PascalCase" in errors[0]


class TestPascalCaseHelper:
	def test_private_pascal_case_class_is_valid(self):
		assert _is_valid_pascal_case("_Resp") is True

	def test_plain_pascal_case_is_valid(self):
		assert _is_valid_pascal_case("UserManager") is True

	def test_lower_camel_case_is_invalid(self):
		assert _is_valid_pascal_case("userManager") is False


class TestSnakeCaseHelper:
	def test_snake_case_is_valid(self):
		assert _is_valid_snake_case("validate_program_access") is True

	def test_camel_case_is_invalid(self):
		assert _is_valid_snake_case("validateProgramAccess") is False


class TestImportOrganization:
	def test_module_docstring_before_imports_is_allowed(self, tmp_path):
		file_path = _write(
			tmp_path,
			"example.py",
			'''
			"""Module docstring."""

			import os

			def foo():
				pass
			''',
		)
		assert check_import_organization(file_path) == []

	def test_import_inside_function_is_not_flagged(self, tmp_path):
		"""A deferred/local import is a deliberate pattern (breaking an
		import cycle, lazy-loading an optional dependency) and must not be
		treated as an out-of-order top-level import."""
		file_path = _write(
			tmp_path,
			"example.py",
			"""
			import os

			def foo():
				import json
				return json.dumps({})
			""",
		)
		assert check_import_organization(file_path) == []

	def test_import_after_module_level_code_is_flagged(self, tmp_path):
		file_path = _write(
			tmp_path,
			"example.py",
			"""
			import os

			x = 1

			import json
			""",
		)
		errors = check_import_organization(file_path)
		assert len(errors) == 1
		assert "top of the file" in errors[0]
