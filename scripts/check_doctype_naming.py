#!/usr/bin/env python3
"""
DocType Naming Convention Checker for Frappe Framework

This script checks for proper DocType naming conventions and field naming.
"""

import re
import sys
import json
from pathlib import Path


def check_doctype_json_file(file_path):
	"""Check DocType JSON files for naming conventions"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			doctype_data = json.load(f)
	except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError):
		return errors
	
	# Check if it's a DocType JSON file
	if not isinstance(doctype_data, dict) or doctype_data.get('doctype') != 'DocType':
		return errors
	
	doctype_name = doctype_data.get('name', '')
	
	# Check DocType name convention (Title Case with Spaces)
	if not _is_valid_doctype_name(doctype_name):
		errors.append(f"DocType name '{doctype_name}' should use Title Case with spaces (e.g., 'Sales Order')")
	
	# Check field naming conventions
	fields = doctype_data.get('fields', [])
	for field in fields:
		if isinstance(field, dict):
			fieldname = field.get('fieldname', '')
			label = field.get('label', '')
			
			# Check fieldname convention (snake_case)
			if fieldname and not _is_valid_field_name(fieldname):
				errors.append(f"Field '{fieldname}' should use snake_case naming")
			
			# Check label convention (Title Case)
			if label and not _is_valid_field_label(label):
				errors.append(f"Field label '{label}' should use Title Case")
	
	return errors


def check_python_doctype_usage(file_path):
	"""Check Python files for proper DocType references"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			content = f.read()
			lines = content.split('\n')
	except (UnicodeDecodeError, FileNotFoundError):
		return errors
	
	for i, line in enumerate(lines, 1):
		# Skip comments
		if line.strip().startswith('#'):
			continue
		
		# Check for hardcoded DocType names that might be incorrect
		doctype_patterns = [
			r'frappe\.get_doc\s*\(\s*["\']([^"\']+)["\']',
			r'frappe\.new_doc\s*\(\s*["\']([^"\']+)["\']',
			r'frappe\.db\.get_value\s*\(\s*["\']([^"\']+)["\']',
			r'frappe\.db\.set_value\s*\(\s*["\']([^"\']+)["\']',
		]
		
		for pattern in doctype_patterns:
			matches = re.finditer(pattern, line)
			for match in matches:
				doctype_name = match.group(1)
				
				# Check if DocType name uses proper convention
				if not _is_valid_doctype_name(doctype_name) and not doctype_name.startswith('tab'):
					errors.append(f"Line {i}: DocType '{doctype_name}' should use Title Case with spaces")
	
	return errors


def check_javascript_doctype_usage(file_path):
	"""Check JavaScript files for proper DocType references"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			content = f.read()
			lines = content.split('\n')
	except (UnicodeDecodeError, FileNotFoundError):
		return errors
	
	for i, line in enumerate(lines, 1):
		# Skip comments
		if line.strip().startswith('//') or line.strip().startswith('/*'):
			continue
		
		# Check for hardcoded DocType names in JavaScript
		js_patterns = [
			r'frappe\.ui\.form\.on\s*\(\s*["\']([^"\']+)["\']',
			r'frappe\.db\.get_value\s*\(\s*["\']([^"\']+)["\']',
			r'frappe\.new_doc\s*\(\s*["\']([^"\']+)["\']',
		]
		
		for pattern in js_patterns:
			matches = re.finditer(pattern, line)
			for match in matches:
				doctype_name = match.group(1)
				
				# Check if DocType name uses proper convention
				if not _is_valid_doctype_name(doctype_name):
					errors.append(f"Line {i}: DocType '{doctype_name}' should use Title Case with spaces")
	
	return errors


def _is_valid_doctype_name(name):
	"""Check if DocType name follows Title Case with Spaces convention"""
	if not name:
		return False
	
	# Should be Title Case with spaces, no underscores or hyphens
	# Examples: "Sales Order", "Item Price", "User"
	return re.match(r'^[A-Z][a-zA-Z\s]*$', name) is not None and '_' not in name and '-' not in name


def _is_valid_field_name(fieldname):
	"""Check if field name follows snake_case convention"""
	if not fieldname:
		return False
	
	# Should be snake_case (lowercase with underscores)
	# Examples: "customer_name", "item_code", "posting_date"
	return re.match(r'^[a-z][a-z0-9_]*$', fieldname) is not None


def _is_valid_field_label(label):
	"""Check if field label follows Title Case convention"""
	if not label:
		return False
	
	# Should be Title Case
	# Examples: "Customer Name", "Item Code", "Posting Date"
	words = label.split()
	return all(word[0].isupper() if word else False for word in words)


def main():
	"""Main function to process files"""
	if len(sys.argv) < 2:
		print("Usage: check_doctype_naming.py <file1> [file2] ...")
		return 0
	
	all_errors = []
	
	for file_path in sys.argv[1:]:
		path = Path(file_path)
		
		if not path.exists():
			continue
		
		errors = []
		
		if path.suffix == '.json' and path.name.endswith('.json'):
			errors.extend(check_doctype_json_file(file_path))
		elif path.suffix == '.py':
			errors.extend(check_python_doctype_usage(file_path))
		elif path.suffix == '.js':
			errors.extend(check_javascript_doctype_usage(file_path))
		
		if errors:
			all_errors.extend([f"{file_path}: {error}" for error in errors])
	
	if all_errors:
		print("❌ DocType naming convention violations found:")
		for error in all_errors:
			print(f"  {error}")
		print("\n💡 DocType naming conventions:")
		print("   ✅ DocType names: Title Case with spaces ('Sales Order', 'Item Price')")
		print("   ✅ Field names: snake_case ('customer_name', 'item_code')")
		print("   ✅ Field labels: Title Case ('Customer Name', 'Item Code')")
		print("   ✅ Method names: snake_case ('validate_customer_details')")
		return 1
	
	return 0


if __name__ == "__main__":
	sys.exit(main())