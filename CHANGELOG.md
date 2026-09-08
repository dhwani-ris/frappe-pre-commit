# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.5] - 2026-09-08

### Fixed
- `frappe-coding-standards` no longer reports two classes of correct code as violations.

  **Class names may carry one leading underscore.** `_is_valid_pascal_case` used
  `^[A-Z][a-zA-Z0-9]*$`, which rejected `_PrivateHelper`. PEP 8 uses a single leading
  underscore to mark something internal to a module, and it is the conventional spelling
  for a private helper class or a test fixture. This was also inconsistent within the
  checker itself: `_is_valid_snake_case` already accepted a leading underscore for
  functions. Genuinely wrong names (`lowercase_class`, `Mixed_Underscore`) are still
  reported.

  **An import inside a function can be marked deliberate.** The import rule flags any
  import appearing after the first non-import line, which includes every function-local
  import. That is a normal Python idiom rather than a mistake: it is how an import cycle
  is broken, and how an expensive module is deferred. The checker cannot distinguish a
  deliberate case from a careless one, so it now lets the author say so with a trailing
  `# frappe-noqa`, optionally followed by a reason. Unmarked function-local imports are
  still reported, so the rule keeps its value.

  The marker is deliberately **not** spelled `# noqa`. That namespace belongs to flake8 and
  ruff, and ruff polices it: `RUF100` reports an "unused blanket noqa directive" for any
  `# noqa` it does not itself need. Since ruff runs alongside this hook in the same
  pre-commit config on a Frappe project, a `# noqa` added to satisfy this checker is then
  flagged by ruff, and the author is stuck between two tools. That is not hypothetical — it
  is what happened on the app this fix came from.

### Why
Both were found on a real Frappe app where the checker blocked a merge. The affected
imports each already carried a comment explaining the cycle they break, and one said in as
many words that the rule was being refused — a signal that the rule needed an escape
hatch rather than that the code needed changing. Without one, the only ways past it are
excluding whole files from the hook or bypassing it, and both cost more coverage than the
rule was buying.

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