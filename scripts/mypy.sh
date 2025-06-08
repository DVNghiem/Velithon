#!/bin/bash
# MyPy type checking script for Velithon

set -e

echo "🔍 Running MyPy type checking..."

# Check if mypy is installed
if ! command -v mypy &> /dev/null; then
    echo "❌ MyPy is not installed. Installing..."
    pip install mypy
fi

# Run mypy on the main package
echo "Checking velithon package..."
mypy velithon/ --ignore-missing-imports --strict-optional --warn-redundant-casts --warn-unused-ignores --check-untyped-defs

# Check tests if requested
if [ "$1" = "--with-tests" ]; then
    echo "Checking tests..."
    mypy tests/ --ignore-missing-imports
fi

echo "✅ MyPy type checking completed successfully!"
