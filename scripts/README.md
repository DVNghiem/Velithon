# Development Scripts

This directory contains scripts to help with development, testing, building, and deployment of Velithon.

## Quick Start

Use the master script `dev.sh` for common tasks:

```bash
# Run full CI pipeline
./scripts/dev.sh ci

# Run tests with coverage
./scripts/dev.sh test

# Lint code
./scripts/dev.sh lint

# Build project
./scripts/dev.sh build

# Install in development mode
./scripts/dev.sh install --dev
```

## Individual Scripts

### 🔍 `mypy.sh` - Type Checking

Runs MyPy type checking on the codebase.

```bash
./scripts/mypy.sh                # Check main package
./scripts/mypy.sh --with-tests   # Include tests
```

### 🔧 `ruff.sh` - Linting and Formatting

Runs Ruff for linting and code formatting.

```bash
./scripts/ruff.sh               # Run linter and formatter
./scripts/ruff.sh check         # Only run linter
./scripts/ruff.sh format        # Only run formatter
./scripts/ruff.sh fix           # Run linter with auto-fix
```

### 🧪 `test-coverage.sh` - Testing with Coverage

Runs pytest with coverage analysis.

```bash
./scripts/test-coverage.sh                    # Basic test run
./scripts/test-coverage.sh --html             # Generate HTML report
./scripts/test-coverage.sh --min-coverage 90  # Set minimum coverage
./scripts/test-coverage.sh -v                 # Verbose output
```

Environment variables:
- `COVERAGE_MIN`: Set minimum coverage threshold (default: 80)

### 🔍 `lint.sh` - Comprehensive Linting

Runs a comprehensive linting suite including:
- Ruff linting
- MyPy type checking
- Bandit security analysis
- Import sorting check (isort)
- Code formatting check (black)

```bash
./scripts/lint.sh
```

Generates `bandit-report.json` with security analysis results.

### 🔨 `build.sh` - Building

Builds the Rust extension and Python package.

```bash
./scripts/build.sh                # Release build
./scripts/build.sh --debug        # Debug build
./scripts/build.sh --clean        # Clean before build
./scripts/build.sh --verbose      # Verbose output
```

### 📦 `install.sh` - Installation

Installs the package in development or production mode.

```bash
./scripts/install.sh              # Editable install (development)
./scripts/install.sh --wheel      # Install from wheel
./scripts/install.sh --dev        # Install with dev dependencies
./scripts/install.sh --force      # Force reinstall
```

### 🚀 `dev.sh` - Master Script

Central script that orchestrates all development tasks.

```bash
./scripts/dev.sh mypy             # Type checking
./scripts/dev.sh ruff [action]    # Linting/formatting
./scripts/dev.sh test [options]   # Testing
./scripts/dev.sh lint             # Full lint suite
./scripts/dev.sh build [options]  # Building
./scripts/dev.sh install [opts]   # Installation
./scripts/dev.sh ci               # Full CI pipeline
./scripts/dev.sh clean            # Clean artifacts
./scripts/dev.sh help             # Show help
```

The `ci` command runs the complete CI pipeline:
1. Comprehensive linting
2. Type checking
3. Tests with coverage (≥80%)
4. Clean build

## Configuration Files

### `ruff.toml`
Ruff configuration for linting and formatting rules.

### `pyproject.toml`
Contains tool configurations for:
- MyPy type checking settings
- Coverage reporting options
- Black formatting rules
- isort import sorting
- Development dependencies

### `pytest.ini`
Pytest configuration including asyncio settings and test paths.

## Common Workflows

### Before Committing
```bash
./scripts/dev.sh ci
```

### Development Setup
```bash
./scripts/dev.sh install --dev
```

### Testing Changes
```bash
./scripts/dev.sh test --html --verbose
```

### Release Build
```bash
./scripts/dev.sh clean
./scripts/dev.sh build --clean
```

### Fixing Code Issues
```bash
./scripts/dev.sh ruff fix    # Auto-fix linting issues
./scripts/dev.sh ruff format # Format code
```

## Requirements

The scripts will automatically install missing tools, but you can install them manually:

```bash
pip install maturin mypy ruff black isort bandit pytest pytest-cov coverage
```

Or use poetry:

```bash
poetry install --with dev
```

## Tips

- All scripts use `set -e` for fail-fast behavior
- Scripts are colored for better readability
- Use `--verbose` flags for detailed output
- Check exit codes for CI/CD integration
- Scripts work from any directory (they find the project root)
