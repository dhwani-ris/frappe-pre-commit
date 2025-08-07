# 🎯 Frappe Pre-commit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

**Comprehensive pre-commit hooks for Frappe Framework projects** to enforce coding standards, security practices, and best practices automatically.

## ✨ Features

- 🛡️ **SQL Injection Prevention** - Detect and prevent SQL injection vulnerabilities
- 📏 **Coding Standards** - Enforce Frappe-specific coding conventions and best practices
- 📝 **DocType Naming** - Validate DocType and field naming conventions
- ⚡ **Fast Execution** - Lightweight checks with minimal dependencies
- 🎯 **Customizable** - Pick and choose hooks based on your project needs

## 🚀 Quick Start

### System Requirements

- **Python**: 3.8 or higher
- **pip**: Latest version
- **pre-commit**: Will be installed automatically
- **Git**: For version control

### Python Path Setup

If you encounter "Executable `python` not found" errors, ensure Python is properly configured:

```bash
# Check Python installation
python3 --version

# Create python symlink if needed (Linux/macOS)
sudo ln -s /usr/bin/python3 /usr/bin/python

# Or add alias to your shell profile (~/.bashrc, ~/.zshrc)
echo 'alias python=python3' >> ~/.bashrc
source ~/.bashrc
```

### For New Frappe Projects

```bash
# 1. Initialize new Frappe app
bench new-app my_custom_app
cd apps/my_custom_app

# 2. Create .pre-commit-config.yaml
curl -o .pre-commit-config.yaml https://raw.githubusercontent.com/dhwani-ris/frappe-pre-commit/main/examples/.pre-commit-config.yaml

# 3. Install and run
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### For Existing Frappe Projects

```bash
# 1. Navigate to your app directory
cd apps/your_app

# 2. Add .pre-commit-config.yaml (see configuration below)
# 3. Install pre-commit
pip install pre-commit
pre-commit install

# 4. Run on existing code
pre-commit run --all-files
```

## 📋 Available Hooks

| Hook ID | Description | Files | Dependencies |
|---------|-------------|-------|--------------|
| `frappe-coding-standards` | General coding standards and best practices | `*.py` | None |
| `frappe-sql-security` | SQL injection and security checks | `*.py` | None |
| `frappe-doctype-naming` | DocType and field naming conventions | `*.py`, `*.js`, `*.json` | `pyyaml` |

## ⚙️ Configuration

### Basic Configuration

Create `.pre-commit-config.yaml` in your project root:

```yaml
repos:
  # Frappe-specific hooks
  - repo: https://github.com/dhwani-ris/frappe-pre-commit
    rev: v1.0.0  # Use latest tag
    hooks:
      - id: frappe-translation-check
      - id: frappe-sql-security
      - id: frappe-coding-standards

  # Code formatting (recommended)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.1
    hooks:
      - id: ruff
        args: ["--select=I", "--fix"]  # Import sorting
      - id: ruff-format  # Code formatting

  # Additional quality checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
```

### Complete Configuration

```yaml
repos:
  # Python formatting and linting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.1
    hooks:
      - id: ruff
        name: "Ruff import sorter"
        args: ["--select=I", "--fix"]
      - id: ruff
        name: "Ruff linter"
        args: ["--extend-ignore=E501"]
      - id: ruff-format
        name: "Ruff formatter"

  # JavaScript/CSS/JSON formatting
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v4.0.0-alpha.8
    hooks:
      - id: prettier
        files: \.(js|jsx|ts|tsx|css|scss|json|md|yml|yaml)$
        exclude: |
          (?x)^(
              .*\.min\.(js|css)$|
              node_modules/.*|
              .*/static/.*
          )$

  # Basic file checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
        exclude: \.(md|rst)$
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements

  # Frappe-specific coding standards
  - repo: https://github.com/dhwani-ris/frappe-pre-commit
    rev: v1.0.0
    hooks:
      - id: frappe-coding-standards 

# Exclude patterns
exclude: |
  (?x)^(
      .*/migrations/.*|
      .*/patches/.*|
      .*\.min\.(js|css)$|
      node_modules/.*|
      __pycache__/.*
  )$
```

### Selective Hook Usage

```yaml
# Use only specific hooks you need
repos:
  - repo: https://github.com/dhwani-ris/frappe-pre-commit
    rev: v1.0.0
    hooks:
      - id: frappe-sql-security     # Only SQL security checks
      - id: frappe-translation-check # Only translation checks
```

## 🔍 What Gets Checked

### 🛡️ SQL Security Checks

**Detects:**
- SQL injection vulnerabilities using `.format()` or f-strings
- String concatenation in SQL queries
- Unencrypted storage of sensitive data (passwords, API keys)

```python
# ❌ Will be flagged
frappe.db.sql("SELECT * FROM tabUser WHERE name = '{}'".format(user_name))
frappe.db.set_value("User", user, "password", plain_password)

# ✅ Correct approach
frappe.db.sql("SELECT * FROM tabUser WHERE name = %s", user_name)
frappe.db.set_value("User", user, "password", frappe.utils.password.encrypt(plain_password))
```


### 📏 Coding Standards

**Enforces:**
- Function length (≤20 lines recommended)
- Proper indentation (tabs, not spaces)
- Naming conventions (snake_case for functions, PascalCase for classes)
- Import organization
- Complexity limits (max nesting depth)

### 📝 DocType Naming Conventions

**Validates:**
- DocType names: Title Case with spaces (`"Sales Order"`)
- Field names: snake_case (`"customer_name"`)
- Field labels: Title Case (`"Customer Name"`)

## 🏗️ Integration Examples

### Integration with Bench

```bash
# For bench-managed projects
cd frappe-bench/apps/your_app

# Add pre-commit config
curl -o .pre-commit-config.yaml https://raw.githubusercontent.com/dhwani-ris/frappe-pre-commit/main/examples/.pre-commit-config.yaml

# Install globally in bench environment
~/frappe-bench/env/bin/pip install pre-commit
~/frappe-bench/env/bin/pre-commit install
```

### Integration with GitHub Actions

Create `.github/workflows/code-quality.yml`:

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install pre-commit
        run: pip install pre-commit
      - name: Run pre-commit
        run: pre-commit run --all-files
```

### Integration with VS Code

Add to `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.sortImports.args": ["--profile", "black"],
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

## 🧪 Development and Testing

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/dhwani-ris/frappe-pre-commit.git
cd frappe-pre-commit

# Create virtual environment
python -m venv dev_env
source dev_env/bin/activate  # On Windows: dev_env\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
pip install pre-commit

# Install pre-commit hooks for this repository
pre-commit install
```

### Running Tests

```bash
# Test individual scripts
python scripts/check_coding_standards.py test_files/sample.py
python scripts/check_sql_security.py test_files/sample.py
python scripts/check_translations.py test_files/sample.py

# Test all hooks
python test_scripts/test_all_hooks.py

# Test with pre-commit
pre-commit run --all-files
```

### Creating Test Files

```bash
# Create test files with issues
mkdir test_project && cd test_project

# Create Python file with intentional issues
cat > bad_example.py << 'EOF'
import frappe

def very_long_function_that_violates_standards():
    frappe.msgprint("Missing translation wrapper")
    result = frappe.db.sql("SELECT * FROM tabUser WHERE name = '{}'".format("test"))
    return result
EOF

# Test your hooks
cd ../
python scripts/check_translations.py test_project/bad_example.py
python scripts/check_sql_security.py test_project/bad_example.py
```

### Testing with Different Frappe Projects

```bash
# Test with ERPNext
cd path/to/erpnext
git clone https://github.com/dhwani-ris/frappe-pre-commit.git .pre-commit-hooks
cp .pre-commit-hooks/examples/.pre-commit-config.yaml .
pre-commit install
pre-commit run --all-files

# Test with custom app
cd path/to/your_custom_app
# Same process as above
```

### Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-check`
3. **Add your hook script** in `scripts/`
4. **Update `.pre-commit-hooks.yaml`**
5. **Add tests** in `test_scripts/`
6. **Update documentation**
7. **Submit pull request**

## 📚 Examples

### Example 1: Basic Frappe App Setup

```bash
# Create new app
cd frappe-bench
bench new-app inventory_management
cd apps/inventory_management

# Add pre-commit
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/dhwani-ris/frappe-pre-commit
    rev: v1.0.0
    hooks:
      - id: frappe-quick-check
EOF

# Install and test
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### Example 2: ERPNext Customization

```bash
# For ERPNext customizations
cd frappe-bench/apps/erpnext

# Use comprehensive config
curl -o .pre-commit-config.yaml https://raw.githubusercontent.com/dhwani-ris/frappe-pre-commit/main/examples/erpnext-config.yaml

pre-commit install
pre-commit run --all-files
```

### Example 3: CI/CD Integration

```yaml
# .github/workflows/quality-check.yml
name: Quality Check

on:
  pull_request:
    branches: [main, develop]

jobs:
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install pre-commit
          pip install -r requirements.txt
      
      - name: Run pre-commit
        run: pre-commit run --all-files
      
      - name: Comment PR
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '❌ Code quality checks failed. Please run `pre-commit run --all-files` locally and fix the issues.'
            })
```

## 🔧 Troubleshooting

### Common Issues

**Pre-commit hooks not running:**
```bash
pre-commit uninstall
pre-commit install
pre-commit run --all-files
```

**Python executable not found error:**
```bash
# Error: Executable `python` not found
# Solution: Create a python symlink or alias

# Option 1: Create symlink (Linux/macOS)
sudo ln -s /usr/bin/python3 /usr/bin/python

# Option 2: Create alias (add to ~/.bashrc or ~/.zshrc)
alias python=python3

# Option 3: Use python3 explicitly in PATH
export PATH="/usr/bin:$PATH"

# Option 4: Install python-is-python3 package (Ubuntu/Debian)
sudo apt install python-is-python3

# After fixing, reinstall pre-commit hooks
pre-commit uninstall
pre-commit install
```

**Hooks failing on large files:**
```bash
# Skip hooks for specific commit
git commit -m "Large file update" --no-verify

# Or exclude large files in config
# Add to .pre-commit-config.yaml:
exclude: |
  (?x)^(
      large_files/.*|
      .*\.min\.js$
  )$
```

**Import errors in scripts:**
```bash
# Make sure Python can find the scripts
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Package installation issues:**
```bash
# If frappe-pre-commit package fails to install automatically
pip install frappe-pre-commit

# Clear pre-commit cache and reinstall
pre-commit clean
pre-commit install
```

### Performance Tips

```bash
# Cache pre-commit environments
export PRE_COMMIT_HOME=~/.cache/pre-commit

# Run only on changed files
pre-commit run

# Skip slow hooks during development
PRE_COMMIT_SKIP=frappe-all-checks git commit -m "Quick fix"
```

## 🤝 Contributing

We welcome contributions! 

### Quick Contribution Steps

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/frappe-pre-commit.git`
3. Create branch: `git checkout -b feature/improvement`
4. Make changes and test thoroughly
5. Submit pull request

### For Developers

If you want to contribute to the package development, testing, or publishing, see [DEVELOPER.md](DEVELOPER.md) for detailed instructions on:
- Setting up the development environment
- Testing changes locally
- Publishing updates to PyPI
- Version management
- Troubleshooting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏢 About

Maintained by **Dhwani RIS** 

- 🌐 **Website**: [dhwaniris.com](https://dhwaniris.com)
- 🐙 **GitHub**: [@dhwani-ris](https://github.com/dhwani-ris)


---

**Ready to improve your Frappe code quality?** Get started with Frappe-Pre-commit today! 🚀

```bash
# Install pre-commit
pip install pre-commit

# Download the pre-commit configuration
curl -o .pre-commit-config.yaml https://raw.githubusercontent.com/dhwani-ris/frappe-pre-commit/main/examples/.pre-commit-config.yaml

# Install the pre-commit hooks (frappe-pre-commit package will be installed automatically)
pre-commit install

# Run all checks
pre-commit run --all-files
```

> **Note**: If you encounter "Executable `python` not found" errors, see the [Python Path Setup](#python-path-setup) section above.