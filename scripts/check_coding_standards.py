#!/usr/bin/env python3
"""
General Coding Standards Checker for Frappe Framework

This script checks for general coding standards compliance including:
- Function length
- Indentation (tabs vs spaces)
- Code structure
- Naming conventions
"""

import re
import sys
import ast
from pathlib import Path


def check_function_length(file_path):
	"""Check if functions are too long (>20 lines)"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			content = f.read()
			tree = ast.parse(content)
	except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
		return errors
	
	for node in ast.walk(tree):
		if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
			if hasattr(node, 'end_lineno') and node.end_lineno:
				func_length = node.end_lineno - node.lineno + 1
				if func_length > 20:
					errors.append(f"Function '{node.name}' at line {node.lineno} is too long ({func_length} lines). Consider breaking it into smaller functions.")
	
	return errors


def check_indentation(file_path):
	"""Check for consistent tab indentation"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			lines = f.readlines()
	except (UnicodeDecodeError, FileNotFoundError):
		return errors
	
	for i, line in enumerate(lines, 1):
		# Check if line starts with spaces and is not empty
		if line.startswith(' ') and line.strip():
			# Count leading spaces
			leading_spaces = len(line) - len(line.lstrip(' '))
			if leading_spaces > 0:
				errors.append(f"Line {i}: Uses {leading_spaces} spaces instead of tabs for indentation")
	
	return errors


def check_naming_conventions(file_path):
	"""Check naming conventions for functions and variables"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			content = f.read()
			tree = ast.parse(content)
	except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
		return errors
	
	for node in ast.walk(tree):
		# Check function names
		if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
			if not _is_valid_snake_case(node.name) and not node.name.startswith('_'):
				errors.append(f"Function '{node.name}' at line {node.lineno} should use snake_case naming")
		
		# Check class names
		elif isinstance(node, ast.ClassDef):
			if not _is_valid_pascal_case(node.name):
				errors.append(f"Class '{node.name}' at line {node.lineno} should use PascalCase naming")
	
	return errors


def check_import_organization(file_path):
	"""Check import organization and style"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			lines = f.readlines()
	except (UnicodeDecodeError, FileNotFoundError):
		return errors
	
	imports_section = True
	non_import_found = False
	
	for i, line in enumerate(lines, 1):
		stripped = line.strip()
		
		# Skip empty lines and comments
		if not stripped or stripped.startswith('#'):
			continue
		
		# Check if it's an import
		if stripped.startswith(('import ', 'from ')):
			if non_import_found:
				errors.append(f"Line {i}: Import should be at the top of the file")
		else:
			# First non-import line found
			if imports_section:
				imports_section = False
				non_import_found = True
	
	return errors


def check_code_complexity(file_path):
	"""Check for overly complex code structures"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			content = f.read()
			lines = content.split('\n')
	except (UnicodeDecodeError, FileNotFoundError):
		return errors
	
	for i, line in enumerate(lines, 1):
		# Check for deeply nested conditions (more than 3 levels)
		if line.strip():
			indentation_level = (len(line) - len(line.lstrip())) // 4  # Assuming 4 spaces = 1 tab
			if indentation_level > 4 and any(keyword in line for keyword in ['if ', 'for ', 'while ', 'try:']):
				errors.append(f"Line {i}: Code is too deeply nested (level {indentation_level}). Consider refactoring.")
		
		# Check for very long lines (>120 characters)
		if len(line) > 120:
			errors.append(f"Line {i}: Line too long ({len(line)} characters). Consider breaking into multiple lines.")
	
	return errors


def check_frappe_specific_patterns(file_path):
	"""Check Frappe-specific coding patterns"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			content = f.read()
			lines = content.split('\n')
	except (UnicodeDecodeError, FileNotFoundError):
		return errors
	
	for i, line in enumerate(lines, 1):
		# Check for deprecated Frappe methods
		deprecated_patterns = [
			(r'\$c_obj\s*\(', 'Use frappe.call() instead of $c_obj()'),
			(r'cur_frm\.set_value', 'Use frm.set_value() instead of cur_frm.set_value()'),
			(r'get_query\s*\(', 'Consider using frappe.db.sql() or Query Builder'),
			(r'add_fetch\s*\(', 'Use frappe.db.get_value() instead of add_fetch()'),
		]
		
		for pattern, message in deprecated_patterns:
			if re.search(pattern, line):
				errors.append(f"Line {i}: {message}")
	
	return errors


def _is_valid_snake_case(name):
	"""Check if name follows snake_case convention"""
	return re.match(r'^[a-z_][a-z0-9_]*$', name) is not None


def _is_valid_pascal_case(name):
	"""Check if name follows PascalCase convention"""
	return re.match(r'^[A-Z][a-zA-Z0-9]*$', name) is not None


def main():
	"""Main function to process files"""
	if len(sys.argv) < 2:
		print("Usage: check_coding_standards.py <file1> [file2] ...")
		return 0
	
	all_errors = []
	
	for file_path in sys.argv[1:]:
		path = Path(file_path)
		
		if not path.exists():
			continue
		
		errors = []
		
		if path.suffix == '.py':
			errors.extend(check_function_length(file_path))
			errors.extend(check_indentation(file_path))
			errors.extend(check_naming_conventions(file_path))
			errors.extend(check_import_organization(file_path))
			errors.extend(check_code_complexity(file_path))
			errors.extend(check_frappe_specific_patterns(file_path))
		
		if errors:
			all_errors.extend([f"{file_path}: {error}" for error in errors])
	
	if all_errors:
		print("❌ Coding standard violations found:")
		for error in all_errors:
			print(f"  {error}")
		print("\n💡 Coding standards:")
		print("   ✅ Use tabs for indentation")
		print("   ✅ Keep functions under 20 lines")
		print("   ✅ Use snake_case for functions and variables")
		print("   ✅ Use PascalCase for classes")
		print("   ✅ Place imports at the top of files")
		print("   ✅ Avoid deep nesting (max 4 levels)")
		print("   ✅ Keep lines under 120 characters")
		return 1
	
	return 0


if __name__ == "__main__":
	sys.exit(main())