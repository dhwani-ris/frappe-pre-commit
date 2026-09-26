# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.6] - Unreleased

### Added
- **Baseline support** for adopting the hooks on an existing codebase. Pre-existing violations are
  recorded in `.frappe-pre-commit-baseline.json`; the hooks then report only new ones.
  - All three hooks read the baseline automatically from the repository root, or from
    `--baseline PATH`. `--no-baseline` reports everything.
  - Violations are fingerprinted by file, rule and a line-number-free key, so unrelated edits do
    not invalidate the baseline. Duplicate violations are counted.
  - Long functions are ratcheted: a baselined function fails if it grows past its recorded length.
- `frappe-pre-commit-baseline` command with `create`, `prune` (shrink only, never adds) and
  `summary`. `create` and `prune` accept `--check` and file paths to update part of the baseline
  without touching the rest.
- Unit test suite (`python -m unittest discover -s tests -t .`).

### Fixed
- Coding standards: unittest's `setUpClass`, `tearDownClass`, `setUpModule`, `tearDownModule`,
  `asyncSetUp` and `asyncTearDown` are no longer reported as naming violations, in any file.
- Coding standards: nesting depth is measured on the syntax tree. Indentation inside docstrings and
  SQL strings is no longer reported, and tab-indented code is measured correctly (it was previously
  divided by four characters, which hid real deep nesting in tab-indented Frappe code).
- DocType naming: labels may contain acronyms (`Season ID`, `CFPP Push Status`), lowercase minor
  words after the first word (`Calls per Minute`) and free text in parentheses (`Details (read-only)`).
  The label checker's own docstring already promised acronyms.
- DocType naming: fieldnames may start with a single `_`, as Frappe's own `_user_tags` do.
- DocType naming: `frappe.ui.form.on("*", ...)` is no longer reported as an invalid DocType name.
- Removed the `frappe-pre-commit-translations` console script, which pointed at a module that does
  not exist.
- README: removed references to the non-existent `frappe-translation-check` hook and
  `check_translations.py`; corrected the documented function-length limit (50, not 20).

### Changed
- Upgrading without a baseline can report nesting violations that 1.0.5 missed in tab-indented code
  (see the nesting fix above). Run `frappe-pre-commit-baseline create` to accept them.

## [1.0.5] - 2026-09-09

### Fixed
- Coding standards: the import-position check walks the syntax tree at module scope, so imports inside
  functions and imports after a module docstring are no longer reported.
- Coding standards: private classes such as `_Resp` are valid PascalCase.

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