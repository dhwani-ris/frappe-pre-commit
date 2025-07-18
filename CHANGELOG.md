# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-07-18

### Added
- Initial release of frappe-pre-commit package
- Four pre-commit hooks for Frappe Framework:
  - `frappe-coding-standards`: General coding standards checker
  - `frappe-translation-check`: Translation wrapper checker
  - `frappe-sql-security`: SQL injection vulnerability checker
  - `frappe-doctype-naming`: DocType naming convention checker
- Comprehensive documentation and examples
- Support for Python 3.8+ and Frappe Framework projects
- Exclusions for hooks.py files in translation checks
- Console script entry points for all hooks

### Technical
- Built with modern Python packaging standards
- Uses pyproject.toml for configuration
- Proper entry points for console scripts
- Comprehensive .gitignore for Python projects
- Developer documentation with publishing guide 