# Development Setup

This guide will help you set up a local development environment for contributing to Velithon.

## Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.10+** (Python 3.12 recommended)
- **Rust** (latest stable version)
- **Poetry** (for dependency management)
- **Git** (for version control)

## Installation Steps

### 1. Clone the Repository

```bash
# Fork the repository on GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/velithon.git
cd velithon

# Add the upstream remote
git remote add upstream https://github.com/DVNghiem/velithon.git
```

### 2. Install Rust

If you don't have Rust installed:

```bash
# Install Rust using rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Verify installation
rustc --version
cargo --version
```

### 3. Install Poetry

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH (if needed)
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
poetry --version
```

### 4. Set Up Python Environment

```bash
# Install Python dependencies
poetry install

# Install development dependencies
poetry install --with dev

# Install documentation dependencies (optional)
poetry install --with docs

# Activate the virtual environment
poetry shell
```

### 5. Build the Rust Extension

```bash
# Build the Rust components
poetry run maturin develop

# Or for release mode (faster)
poetry run maturin develop --release
```

### 6. Verify Installation

```bash
# Run a simple test
python -c "import velithon; print('Velithon imported successfully!')"

# Run the test suite
poetry run pytest

# Check code style
poetry run ruff check
poetry run black --check .
```

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a new feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Edit the code using your preferred editor. For Velithon development:

- **Python code** is in the `velithon/` directory
- **Rust code** is in the `src/` directory
- **Documentation** is in the `docs/` directory
- **Tests** are in the `tests/` directory

### 3. Build and Test

```bash
# Rebuild after Rust changes
poetry run maturin develop

# Run tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_application.py

# Run with coverage
poetry run pytest --cov=velithon --cov-report=html
```

### 4. Code Style and Linting

```bash
# Format code
poetry run black .
poetry run isort .

# Check for issues
poetry run ruff check
poetry run bandit -r velithon/

# Fix auto-fixable issues
poetry run ruff check --fix
```

### 5. Documentation

```bash
# Build documentation (if working on docs)
poetry run mkdocs serve

# This will start a local server at http://127.0.0.1:8000
```

## Useful Commands

### Poetry Commands

```bash
# Add a new dependency
poetry add package-name

# Add a development dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Show dependency tree
poetry show --tree

# Export requirements
poetry export -f requirements.txt --output requirements.txt
```

### Testing Commands

```bash
# Run all tests
poetry run pytest

# Run tests with verbose output
poetry run pytest -v

# Run tests in parallel
poetry run pytest -n auto

# Run specific test class
poetry run pytest tests/test_application.py::TestVelithon

# Run with coverage and HTML report
poetry run pytest --cov=velithon --cov-report=html
```

### Benchmarking

```bash
# Run performance benchmarks
poetry run python benchmarks/simple_benchmark.py

# Run with pytest-benchmark
poetry run pytest benchmarks/ --benchmark-only
```

## IDE Setup

### VS Code

Recommended extensions:
- Python
- Rust-analyzer
- Black Formatter
- isort
- Pylance

Recommended settings (`.vscode/settings.json`):

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "rust-analyzer.cargo.target": "x86_64-unknown-linux-gnu"
}
```

### PyCharm

1. Open the project directory
2. Configure Python interpreter to use Poetry's virtual environment
3. Enable Rust plugin for Rust code editing

## Troubleshooting

### Common Issues

1. **Rust compilation errors**
   ```bash
   # Update Rust toolchain
   rustup update
   
   # Clean build cache
   cargo clean
   ```

2. **Poetry environment issues**
   ```bash
   # Remove virtual environment
   poetry env remove python
   
   # Recreate environment
   poetry install
   ```

3. **Import errors**
   ```bash
   # Rebuild the extension
   poetry run maturin develop --release
   ```

4. **Test failures**
   ```bash
   # Check if all dependencies are installed
   poetry install --with dev
   
   # Run tests with more verbose output
   poetry run pytest -vvv
   ```

### Getting Help

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting)
2. Search existing [GitHub issues](https://github.com/DVNghiem/velithon/issues)
3. Ask for help in [GitHub discussions](https://github.com/DVNghiem/velithon/discussions)
4. Join our community chat (if available)

## Next Steps

Once your development environment is set up:

1. Read the [code style guidelines](code-style.md)
2. Learn about [testing practices](testing.md)
3. Understand the [documentation process](documentation.md)
4. Pick an issue to work on or propose a new feature
