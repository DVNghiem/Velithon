#!/bin/bash
# Comprehensive linting script for Velithon

set -e

echo "🔍 Running comprehensive linting suite..."

# Function to check and install tools
check_and_install() {
    local tool=$1
    local package=${2:-$tool}
    
    if ! command -v $tool &> /dev/null; then
        echo "❌ $tool is not installed. Installing $package..."
        pip install $package
    fi
}

# Install required tools
check_and_install "ruff"
check_and_install "mypy"
check_and_install "bandit"
check_and_install "black"
check_and_install "isort"

echo ""
echo "1️⃣ Running Ruff linter..."
ruff check velithon/ tests/ benchmarks/

echo ""
echo "2️⃣ Running MyPy type checking..."
mypy velithon/ --ignore-missing-imports --strict-optional --warn-redundant-casts --warn-unused-ignores --check-untyped-defs

echo ""
echo "3️⃣ Running Bandit security linter..."
bandit -r velithon/ -f json -o bandit-report.json || true
bandit -r velithon/ || echo "⚠️  Bandit found potential security issues"

echo ""
echo "4️⃣ Checking import sorting with isort..."
isort --check-only --diff velithon/ tests/ benchmarks/ || echo "⚠️  Import sorting issues found"

echo ""
echo "5️⃣ Checking code formatting with black..."
black --check --diff velithon/ tests/ benchmarks/ || echo "⚠️  Code formatting issues found"

echo ""
echo "✅ Linting suite completed!"
echo "📄 Security report saved to bandit-report.json"
