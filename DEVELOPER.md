# Developer Guide

This guide covers how to develop, test, and publish the `frappe-pre-commit` package.

## Development Setup

### 1. Install Development Dependencies

```bash
# Install the package in editable mode
pip install -e .

# Install build tools
pip install build twine
```

### 2. Test Locally

```bash
# Test the console scripts
frappe-pre-commit-coding-standards --help
frappe-pre-commit-translations --help
frappe-pre-commit-sql-security --help
frappe-pre-commit-doctype-naming --help

# Test with actual files
frappe-pre-commit-coding-standards scripts/check_coding_standards.py
```

## Publishing to PyPI

### First Time Setup

1. **Create PyPI Account**
   - Go to https://pypi.org/account/register/
   - Create an account and verify your email

2. **Create TestPyPI Account** (Recommended)
   - Go to https://test.pypi.org/account/register/
   - Create an account (can use same username as PyPI)
   - Verify your email

3. **Configure Authentication** (Optional)
   Create `~/.pypirc` for easier uploads:
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = your_pypi_token

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = your_testpypi_token
   ```

### Publishing Process

#### Step 1: Update Version

Before publishing, update the version in `pyproject.toml`:

```toml
[project]
name = "frappe-pre-commit"
version = "1.0.1"  # Increment version
```

#### Step 2: Build Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build the package
python3 -m build
```

#### Step 3: Test Package

```bash
# Check package validity
twine check dist/*

# Test installation from local files
pip install dist/frappe_pre_commit-1.0.1-py3-none-any.whl
```

#### Step 4: Upload to TestPyPI (Recommended)

```bash
# Upload to test PyPI first
twine upload --repository testpypi dist/*

# Test installation from test PyPI
pip install --index-url https://test.pypi.org/simple/ frappe-pre-commit
```

#### Step 5: Upload to PyPI

```bash
# Upload to production PyPI
twine upload dist/*
```

#### Step 6: Verify Installation

```bash
# Test the published package
pip install frappe-pre-commit
frappe-pre-commit-coding-standards --help
```

## Updating the Package

### For Bug Fixes (Patch Version)

1. **Fix the bug** in the appropriate script
2. **Update version** in `pyproject.toml`:
   ```toml
   version = "1.0.2"  # Increment patch version
   ```
3. **Test locally**:
   ```bash
   pip install -e .
   # Test your changes
   ```
4. **Build and publish**:
   ```bash
   python3 -m build
   twine upload dist/*
   ```

### For New Features (Minor Version)

1. **Add new features** to scripts
2. **Update version** in `pyproject.toml`:
   ```toml
   version = "1.1.0"  # Increment minor version
   ```
3. **Update documentation** (README.md, this file)
4. **Test thoroughly**:
   ```bash
   pip install -e .
   # Test all features
   ```
5. **Build and publish**:
   ```bash
   python3 -m build
   twine upload dist/*
   ```

### For Breaking Changes (Major Version)

1. **Make breaking changes**
2. **Update version** in `pyproject.toml`:
   ```toml
   version = "2.0.0"  # Increment major version
   ```
3. **Update documentation** with migration guide
4. **Test extensively**
5. **Build and publish**:
   ```bash
   python3 -m build
   twine upload dist/*
   ```

## Version Management

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH**
- **PATCH**: Bug fixes (1.0.0 → 1.0.1)
- **MINOR**: New features, backward compatible (1.0.0 → 1.1.0)
- **MAJOR**: Breaking changes (1.0.0 → 2.0.0)

## Testing

### Test Scripts Individually

```bash
# Test coding standards
python scripts/check_coding_standards.py scripts/check_coding_standards.py

# Test translations
python scripts/check_translations.py scripts/check_translations.py

# Test SQL security
python scripts/check_sql_security.py scripts/check_sql_security.py

# Test doctype naming
python scripts/check_doctype_naming.py scripts/check_doctype_naming.py
```

### Test with Pre-commit

```bash
# In another project
pip install frappe-pre-commit
curl -o .pre-commit-config.yaml https://raw.githubusercontent.com/dhwani-ris/frappe-pre-commit/main/examples/.pre-commit-config.yaml
pre-commit install
pre-commit run --all-files
```

## Troubleshooting

### Build Issues

```bash
# Clean everything and rebuild
rm -rf dist/ build/ *.egg-info/
pip install -e .
python3 -m build
```

### Upload Issues

```bash
# Check package validity
twine check dist/*

# Test upload to test PyPI first
twine upload --repository testpypi dist/*
```

### Installation Issues

```bash
# Uninstall and reinstall
pip uninstall frappe-pre-commit -y
pip install frappe-pre-commit

# Check if scripts are available
which frappe-pre-commit-coding-standards
```

## GitHub Workflow Integration

For CI/CD, add this to your `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build and publish
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: |
        python -m build
        twine upload dist/*
```

## Alternative: GitHub Packages

If you prefer GitHub Packages over PyPI:

1. **Create GitHub token** with `write:packages` permission
2. **Configure twine**:
   ```ini
   [distutils]
   index-servers =
       github

   [github]
   repository = https://github.com/dhwani-ris/frappe-pre-commit
   username = __token__
   password = your_github_token
   ```
3. **Upload**:
   ```bash
   twine upload --repository github dist/*
   ```

## Maintenance

### Regular Tasks

1. **Update dependencies** in `pyproject.toml`
2. **Test with latest Python versions**
3. **Update documentation** as needed
4. **Monitor for issues** in GitHub issues

### Security

- Keep dependencies updated
- Monitor for security vulnerabilities
- Use `pip-audit` to check for known vulnerabilities

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
- Create an issue on GitHub
- Check existing issues for solutions
- Review the main README.md for usage instructions 