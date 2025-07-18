#!/usr/bin/env python3
"""
Translation Wrapper Checker for Frappe Framework

This script checks if user-facing strings are properly wrapped in translation functions.
- Python: _("string")
- JavaScript: __("string")
"""

import re
import sys
import ast
from pathlib import Path


def check_python_translations(file_path):
	"""Check Python files for missing translation wrappers"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			content = f.read()
			lines = content.split('\n')
	except (UnicodeDecodeError, FileNotFoundError):
		return errors
	
	# Python patterns that should be translated
	python_patterns = [
		(r'frappe\.msgprint\s*\(\s*["\']([^"\']+)["\'](?!\s*%)', 'frappe.msgprint'),
		(r'frappe\.throw\s*\(\s*["\']([^"\']+)["\'](?!\s*%)', 'frappe.throw'),
		(r'frappe\.log_error\s*\(\s*["\']([^"\']+)["\'](?!\s*%)', 'frappe.log_error'),
		(r'return\s+["\']([^"\']{10,})["\']', 'return statement'),
		(r'title\s*=\s*["\']([^"\']+)["\']', 'title assignment'),
		(r'label\s*=\s*["\']([^"\']+)["\']', 'label assignment'),
	]
	
	for i, line in enumerate(lines, 1):
		# Skip comments and docstrings
		if line.strip().startswith('#') or '"""' in line or "'''" in line:
			continue
			
		for pattern, context in python_patterns:
			matches = re.finditer(pattern, line)
			for match in matches:
				string_content = match.group(1)
				
				# Skip if string is too short or looks like code
				if len(string_content) < 3 or _looks_like_code(string_content):
					continue
				
				# Check if already wrapped in _() 
				if not re.search(r'_\s*\(\s*["\']' + re.escape(string_content), line):
					errors.append(f"Line {i}: Missing translation wrapper in {context}: '{string_content}'")
	
	return errors


def check_javascript_translations(file_path):
	"""Check JavaScript files for missing translation wrappers"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			content = f.read()
			lines = content.split('\n')
	except (UnicodeDecodeError, FileNotFoundError):
		return errors
	
	# JavaScript patterns that should be translated
	js_patterns = [
		(r'frappe\.msgprint\s*\(\s*["\']([^"\']+)["\']', 'frappe.msgprint'),
		(r'frappe\.throw\s*\(\s*["\']([^"\']+)["\']', 'frappe.throw'),
		(r'alert\s*\(\s*["\']([^"\']+)["\']', 'alert'),
		(r'title:\s*["\']([^"\']+)["\']', 'title property'),
		(r'label:\s*["\']([^"\']+)["\']', 'label property'),
	]
	
	for i, line in enumerate(lines, 1):
		# Skip comments
		if line.strip().startswith('//') or line.strip().startswith('/*'):
			continue
			
		for pattern, context in js_patterns:
			matches = re.finditer(pattern, line)
			for match in matches:
				string_content = match.group(1)
				
				# Skip if string is too short or looks like code
				if len(string_content) < 3 or _looks_like_code(string_content):
					continue
				
				# Check if already wrapped in __()
				if not re.search(r'__\s*\(\s*["\']' + re.escape(string_content), line):
					errors.append(f"Line {i}: Missing translation wrapper in {context}: '{string_content}'")
	
	return errors


def _looks_like_code(string_content):
	"""Check if string looks like code rather than user text"""
	code_indicators = [
		'.',  # Method calls
		'_',  # Private variables
		'==', '!=', '>=', '<=',  # Operators
		'true', 'false', 'null',  # Boolean/null values
		'function', 'var', 'let', 'const',  # JS keywords
		'def ', 'class ', 'import ',  # Python keywords
	]
	
	# Check if string contains code indicators
	content_lower = string_content.lower()
	return any(indicator in content_lower for indicator in code_indicators)


def main():
	"""Main function to process files"""
	if len(sys.argv) < 2:
		print("Usage: check_translations.py <file1> [file2] ...")
		return 0
	
	all_errors = []
	
	for file_path in sys.argv[1:]:
		path = Path(file_path)
		
		if not path.exists():
			continue
			
		if path.suffix == '.py':
			errors = check_python_translations(file_path)
		elif path.suffix == '.js':
			errors = check_javascript_translations(file_path)
		else:
			continue
			
		if errors:
			all_errors.extend([f"{file_path}: {error}" for error in errors])
	
	if all_errors:
		print("❌ Translation wrapper errors found:")
		for error in all_errors:
			print(f"  {error}")
		print("\n💡 Fix by wrapping strings in:")
		print("   Python: _('Your message')")
		print("   JavaScript: __('Your message')")
		return 1
	
	return 0


if __name__ == "__main__":
	sys.exit(main())