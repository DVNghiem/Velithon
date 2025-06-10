#!/bin/bash
# Ruff linting and formatting script for Velithon

set -e

echo "🔧 Running Ruff linting and formatting..."

# Check if ruff is installed
if ! command -v ruff &> /dev/null; then
    echo "❌ Ruff is not installed. Installing..."
    pip install ruff
fi

# Default action is both check and format
ACTION=${1:-"all"}

case $ACTION in
    "check")
        echo "Running Ruff linter (check only)..."
        ruff check velithon/ tests/ benchmarks/
        ;;
    "format")
        echo "Running Ruff formatter..."
        ruff format velithon/ tests/ benchmarks/
        ;;
    "fix")
        echo "Running Ruff linter with auto-fix..."
        ruff check --fix velithon/ tests/ benchmarks/
        ;;
    "all"|*)
        echo "Running Ruff linter..."
        ruff check velithon/ tests/ benchmarks/
        echo "Running Ruff formatter..."
        ruff format velithon/ tests/ benchmarks/
        ;;
esac

echo "✅ Ruff completed successfully!"
