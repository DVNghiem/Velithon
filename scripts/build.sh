#!/bin/bash
# Build script for Velithon

set -e

echo "🔨 Building Velithon..."

# Parse arguments
BUILD_TYPE="release"
CLEAN=""
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            BUILD_TYPE="debug"
            shift
            ;;
        --clean)
            CLEAN="--clean"
            shift
            ;;
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        *)
            echo "Unknown option $1"
            echo "Usage: $0 [--debug] [--clean] [-v|--verbose]"
            exit 1
            ;;
    esac
done

# Check if maturin is installed
if ! command -v maturin &> /dev/null; then
    echo "❌ Maturin is not installed. Installing..."
    pip install maturin
fi

# Clean if requested
if [ ! -z "$CLEAN" ]; then
    echo "🧹 Cleaning previous builds..."
    rm -rf target/
    rm -rf dist/
    rm -rf build/
    find . -name "*.so" -delete
    find . -name "*.pyd" -delete
fi

# Build based on type
if [ "$BUILD_TYPE" = "debug" ]; then
    echo "Building in debug mode..."
    maturin develop $VERBOSE
else
    echo "Building in release mode..."
    maturin build --release $VERBOSE
fi

echo ""
echo "✅ Build completed successfully!"

if [ "$BUILD_TYPE" = "release" ]; then
    echo "📦 Built wheels are available in dist/"
    ls -la dist/ 2>/dev/null || echo "No dist/ directory found"
fi
