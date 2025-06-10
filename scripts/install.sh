#!/bin/bash
# Installation script for Velithon

set -e

echo "📦 Installing Velithon..."

# Parse arguments
INSTALL_TYPE="editable"
FORCE=""
DEV_DEPS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --wheel)
            INSTALL_TYPE="wheel"
            shift
            ;;
        --force)
            FORCE="--force-reinstall"
            shift
            ;;
        --dev)
            DEV_DEPS="true"
            shift
            ;;
        *)
            echo "Unknown option $1"
            echo "Usage: $0 [--wheel] [--force] [--dev]"
            exit 1
            ;;
    esac
done

# Check if maturin is installed
if ! command -v maturin &> /dev/null; then
    echo "❌ Maturin is not installed. Installing..."
    pip install maturin
fi

# Install based on type
case $INSTALL_TYPE in
    "wheel")
        echo "Building and installing from wheel..."
        maturin build --release
        pip install $FORCE dist/*.whl
        ;;
    "editable"|*)
        echo "Installing in editable/development mode..."
        maturin develop $FORCE
        ;;
esac

# Install development dependencies if requested
if [ "$DEV_DEPS" = "true" ]; then
    echo ""
    echo "📚 Installing development dependencies..."
    
    # Install poetry if not available
    if ! command -v poetry &> /dev/null; then
        echo "Installing poetry..."
        pip install poetry
    fi
    
    # Install dev dependencies
    poetry install --with dev
    
    # Also install common development tools
    pip install mypy ruff black isort bandit pytest pytest-cov coverage
fi

echo ""
echo "✅ Installation completed successfully!"

# Verify installation
echo ""
echo "🔍 Verifying installation..."
python -c "import velithon; print(f'Velithon version: {velithon.__version__ if hasattr(velithon, \"__version__\") else \"unknown\"}')" || echo "⚠️  Could not import velithon"

# Check CLI
if command -v velithon &> /dev/null; then
    echo "✅ Velithon CLI is available"
else
    echo "⚠️  Velithon CLI not found in PATH"
fi
