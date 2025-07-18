#!/usr/bin/env python3
"""
SQL Security Checker for Frappe Framework

This script checks for SQL injection vulnerabilities and enforces secure SQL practices.
"""

import re
import sys
from pathlib import Path


def check_sql_injection_patterns(file_path):
	"""Check for SQL injection vulnerabilities in Python files"""
	errors = []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			content = f.read()
			lines = content.split('\n')
	except (UnicodeDecodeError, FileNotFoundError):
		return errors
	
	# Dangerous SQL patterns
	dangerous_patterns = [
		(r'frappe\.db\.sql\s*\(\s*["\'][^"\']*\.format\s*\([^)]*\)', 
		 'SQL query using .format() - use parameterized queries with %s'),
		(r'frappe\.db\.sql\s*\(\s*["\'][^"\']*\{\}[^"\']*["\']', 
		 'SQL query with {} formatting - use %s parameters instead'),
		(r'frappe\.db\.sql\s*\(\s*["\'][^"\']*["\'][^,)]*\+', 
		 'SQL query with string concatenation - use parameterized queries'),
		(r'frappe\.db\.sql\s*\(\s*f["\']', 
		 'SQL query using f-strings - use parameterized queries with %s'),
		(r'frappe\.db\.sql\s*\(\s*["\'][^"\']*%[sd][^"\']*["\'][^,)]*%', 
		 'SQL query using % formatting - use parameterized queries'),
	]
	
	# Patterns for unencrypted sensitive data
	encryption_patterns = [
		(r'frappe\.db\.set_value\s*\([^)]*password[^)]*["\'][^"\']+["\']', 
		 'Storing password without encryption - use frappe.utils.password.encrypt()'),
		(r'frappe\.db\.set_value\s*\([^)]*api_key[^)]*["\'][^"\']+["\']', 
		 'Storing API key without encryption - use frappe.utils.password.encrypt()'),
		(r'frappe\.db\.set_value\s*\([^)]*secret[^)]*["\'][^"\']+["\']', 
		 'Storing secret without encryption - use frappe.utils.password.encrypt()'),
	]
	
	for i, line in enumerate(lines, 1):
		# Skip comments
		if line.strip().startswith('#'):
			continue
		
		# Check for SQL injection patterns
		if 'frappe.db.sql' in line:
			for pattern, message in dangerous_patterns:
				if re.search(pattern, line, re.IGNORECASE):
					errors.append(f"Line {i}: {message}")
		
		# Check for unencrypted sensitive data
		if 'frappe.db.set_value' in line:
			for pattern, message in encryption_patterns:
				if re.search(pattern, line, re.IGNORECASE):
					errors.append(f"Line {i}: {message}")
	
	return errors


def check_query_builder_usage(file_path):
	"""Check for proper Query Builder usage"""
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
		
		# Check for complex SQL that should use Query Builder
		if 'frappe.db.sql' in line and any(keyword in line.upper() for keyword in ['JOIN', 'UNION', 'SUBQUERY']):
			if len(line) > 120:  # Long complex queries
				errors.append(f"Line {i}: Consider using Query Builder for complex SQL queries")
	
	return errors


def check_permission_queries(file_path):
	"""Check for proper permission handling in queries"""
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
		
		# Check for queries without permission checks
		if 'frappe.db.sql' in line and 'SELECT' in line.upper():
			# Look for potential DocType queries without permission checks
			if 'tab' in line and not any(perm in content for perm in ['has_permission', 'get_permitted_documents']):
				# This is a heuristic check - may need refinement
				pass  # Could add warning about permission checks
	
	return errors


def main():
	"""Main function to process files"""
	if len(sys.argv) < 2:
		print("Usage: check_sql_security.py <file1> [file2] ...")
		return 0
	
	all_errors = []
	
	for file_path in sys.argv[1:]:
		path = Path(file_path)
		
		if not path.exists() or path.suffix != '.py':
			continue
		
		errors = []
		errors.extend(check_sql_injection_patterns(file_path))
		errors.extend(check_query_builder_usage(file_path))
		errors.extend(check_permission_queries(file_path))
		
		if errors:
			all_errors.extend([f"{file_path}: {error}" for error in errors])
	
	if all_errors:
		print("❌ SQL security issues found:")
		for error in all_errors:
			print(f"  {error}")
		print("\n💡 Security best practices:")
		print("   ✅ Use parameterized queries: frappe.db.sql('SELECT * FROM tabUser WHERE name = %s', username)")
		print("   ✅ Encrypt sensitive data: frappe.utils.password.encrypt(password)")
		print("   ✅ Use Query Builder for complex queries")
		print("   ✅ Always check permissions before data access")
		return 1
	
	return 0


if __name__ == "__main__":
	sys.exit(main())