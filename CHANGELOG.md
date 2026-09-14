# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.6] - 2026-09-14

### Fixed
- `frappe-coding-standards`: `check_naming_conventions` only exempted `setUp`/
  `tearDown` from the snake_case rule in `test_*.py` files. `setUpClass`,
  `tearDownClass`, `setUpModule` and `tearDownModule` are equally
  unittest-mandated method names - the framework calls them by that exact
  name, so renaming them to snake_case makes the fixture silently stop
  running. All six lifecycle names are now exempted (`UNITTEST_LIFECYCLE_METHODS`).
- Removed dead duplicated code in `check_naming_conventions` (the file-name
  and exemption checks were each computed twice) and a duplicate `import os`
  at module level.

### Added
- `tests/test_check_coding_standards.py`: regression tests for the naming
  convention checker (unittest lifecycle exemption, snake_case/PascalCase
  helpers) and the import-organization checker (module docstrings, deferred
  imports, genuinely misplaced imports). Install with the `dev` extra
  (`pip install -e ".[dev]"`) and run with `pytest`.

## [1.0.5] - 2026-09-09

### Fixed
- `frappe-coding-standards`: `_is_valid_pascal_case` rejected private classes
  (`_Resp`, `_SendCase`) because a leading underscore failed the PascalCase
  regex, even though `check_naming_conventions` already grants private
  *functions* this exemption. The regex now allows an optional leading
  underscore.
- `frappe-coding-standards`: `check_import_organization` scanned raw lines and
  flagged any import after the first non-import line, which included imports
  nested inside a function or method - a deliberate pattern Frappe code uses
  to break import cycles and defer optional dependencies. The check now walks
  the AST and only considers module-level imports; a module docstring ahead
  of the imports is no longer miscounted either.

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