#!/bin/bash
# Pytest with coverage script for Velithon

set -e

echo "🧪 Running pytest with coverage..."

# Check if pytest and coverage are installed
if ! command -v pytest &> /dev/null; then
    echo "❌ Pytest is not installed. Installing..."
    pip install pytest pytest-cov
fi

if ! command -v coverage &> /dev/null; then
    echo "❌ Coverage is not installed. Installing..."
    pip install coverage
fi

# Parse arguments
COVERAGE_MIN=${COVERAGE_MIN:-80}
HTML_REPORT=""
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --html)
            HTML_REPORT="--cov-report=html"
            shift
            ;;
        --min-coverage)
            COVERAGE_MIN="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        *)
            # Pass through other arguments to pytest
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
    esac
done

# Run tests with coverage
echo "Running tests with coverage analysis..."
pytest $VERBOSE \
    --cov=velithon \
    --cov-report=term-missing \
    --cov-report=xml \
    $HTML_REPORT \
    --cov-fail-under=$COVERAGE_MIN \
    $PYTEST_ARGS \
    tests/

# Generate coverage summary
echo ""
echo "📊 Coverage Summary:"
coverage report --show-missing

if [ ! -z "$HTML_REPORT" ]; then
    echo "📄 HTML coverage report generated in htmlcov/"
fi

echo "✅ Tests completed successfully with coverage >= ${COVERAGE_MIN}%!"
