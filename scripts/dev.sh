#!/bin/bash
# Master script for all development tasks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo "Velithon Development Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  mypy              Run MyPy type checking"
    echo "  ruff [action]     Run Ruff linter/formatter (check|format|fix|all)"
    echo "  test              Run pytest with coverage"
    echo "  lint              Run comprehensive linting suite"
    echo "  build [options]   Build the project"
    echo "  install [options] Install the project"
    echo "  ci                Run full CI pipeline"
    echo "  clean             Clean build artifacts"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 mypy"
    echo "  $0 ruff format"
    echo "  $0 test --html"
    echo "  $0 build --clean"
    echo "  $0 install --dev"
    echo "  $0 ci"
}

run_ci_pipeline() {
    echo -e "${BLUE}🚀 Running CI Pipeline...${NC}"
    echo ""
    
    echo -e "${YELLOW}Step 1: Linting${NC}"
    "$SCRIPT_DIR/lint.sh"
    echo ""
    
    echo -e "${YELLOW}Step 2: Type Checking${NC}"
    "$SCRIPT_DIR/mypy.sh"
    echo ""
    
    echo -e "${YELLOW}Step 3: Testing with Coverage${NC}"
    "$SCRIPT_DIR/test-coverage.sh" --min-coverage 80
    echo ""
    
    echo -e "${YELLOW}Step 4: Building${NC}"
    "$SCRIPT_DIR/build.sh" --clean
    echo ""
    
    echo -e "${GREEN}✅ CI Pipeline completed successfully!${NC}"
}

clean_artifacts() {
    echo -e "${BLUE}🧹 Cleaning build artifacts...${NC}"
    
    # Remove build directories
    rm -rf target/
    rm -rf dist/
    rm -rf build/
    rm -rf htmlcov/
    rm -rf .coverage
    rm -rf coverage.xml
    rm -rf bandit-report.json
    
    # Remove Python cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    
    # Remove compiled extensions
    find . -name "*.so" -delete 2>/dev/null || true
    find . -name "*.pyd" -delete 2>/dev/null || true
    
    echo -e "${GREEN}✅ Cleanup completed!${NC}"
}

# Main script logic
if [ $# -eq 0 ]; then
    print_usage
    exit 1
fi

COMMAND=$1
shift

case $COMMAND in
    "mypy")
        "$SCRIPT_DIR/mypy.sh" "$@"
        ;;
    "ruff")
        "$SCRIPT_DIR/ruff.sh" "$@"
        ;;
    "test")
        "$SCRIPT_DIR/test-coverage.sh" "$@"
        ;;
    "lint")
        "$SCRIPT_DIR/lint.sh" "$@"
        ;;
    "build")
        "$SCRIPT_DIR/build.sh" "$@"
        ;;
    "install")
        "$SCRIPT_DIR/install.sh" "$@"
        ;;
    "ci")
        run_ci_pipeline
        ;;
    "clean")
        clean_artifacts
        ;;
    "help"|"--help"|"-h")
        print_usage
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $COMMAND${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac
