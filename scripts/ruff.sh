#!/bin/bash
# Usage: ./ruff.sh [check|format|fix|all] [--dry-run] [--verbose] [--config=<path>]
#
# Options:
#   check        Run Ruff linter without making changes
#   format       Run Ruff formatter
#   fix          Run Ruff linter with auto-fix
#   all          Run both linter and formatter (default)
#   --dry-run    Simulate actions without making changes
#   --verbose    Enable detailed output
#   --config     Specify custom Ruff configuration file

# set -euo pipefail

# ANSI color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_verbose() { [[ "$VERBOSE" == "true" ]] && echo -e "[VERBOSE] $1"; }

# Default configuration
ACTION="all"
DRY_RUN="false"
VERBOSE="false"
CONFIG_FILE=""
DEFAULT_DIRS=("velithon" "tests" "benchmarks")
EXIT_CODE=0

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        check|format|fix|all)
            ACTION="$1"
            shift
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --verbose)
            VERBOSE="true"
            shift
            ;;
        --config=*)
            CONFIG_FILE="${1#*=}"
            shift
            ;;
        *)
            log_error "Unknown argument: $1"
            echo "Usage: $0 [check|format|fix|all] [--dry-run] [--verbose] [--config=<path>]"
            exit 1
            ;;
    esac
done

# Print configuration if verbose
log_verbose "Action: $ACTION"
log_verbose "Dry run: $DRY_RUN"
log_verbose "Verbose: $VERBOSE"
log_verbose "Config file: ${CONFIG_FILE:-default}"
log_verbose "Target directories: ${DEFAULT_DIRS[*]}"

# Check if Ruff is installed
if ! command -v ruff &> /dev/null; then
    log_warning "Ruff is not installed. Attempting to install..."
    if ! pip install ruff; then
        log_error "Failed to install Ruff. Please install it manually."
        exit 1
    fi
    log_info "Ruff installed successfully."
fi

# Build Ruff command options
RUFF_OPTS=()
[[ -n "$CONFIG_FILE" ]] && RUFF_OPTS+=("--config" "$CONFIG_FILE")
[[ "$DRY_RUN" == "true" ]] && RUFF_OPTS+=("--no-fix")
[[ "$VERBOSE" == "true" ]] && RUFF_OPTS+=("--verbose")

# Validate directories
for dir in "${DEFAULT_DIRS[@]}"; do
    if [[ ! -d "$dir" ]]; then
        log_warning "Directory $dir does not exist. Skipping..."
        continue
    fi
done

# Execute Ruff commands based on action
case "$ACTION" in
    "check")
        log_info "Running Ruff linter (check only)..."
        if ! ruff check "${RUFF_OPTS[@]}" "${DEFAULT_DIRS[@]}"; then
            EXIT_CODE=1
            log_error "Ruff linter found issues."
        fi
        ;;
    "format")
        log_info "Running Ruff formatter..."
        if [[ "$DRY_RUN" == "true" ]]; then
            ruff format --check "${RUFF_OPTS[@]}" "${DEFAULT_DIRS[@]}"
        else
            ruff format "${RUFF_OPTS[@]}" "${DEFAULT_DIRS[@]}"
        fi
        ;;
    "fix")
        log_info "Running Ruff linter with auto-fix..."
        if ! ruff check --fix "${RUFF_OPTS[@]}" "${DEFAULT_DIRS[@]}"; then
            EXIT_CODE=1
            log_warning "Some issues could not be auto-fixed."
        fi
        ;;
    "all")
        log_info "Running Ruff linter..."
        if ! ruff check "${RUFF_OPTS[@]}" "${DEFAULT_DIRS[@]}"; then
            EXIT_CODE=1
            log_error "Ruff linter found issues."
        fi
        log_info "Running Ruff formatter..."
        if [[ "$DRY_RUN" == "true" ]]; then
            ruff format --check "${RUFF_OPTS[@]}" "${DEFAULT_DIRS[@]}"
        else
            ruff format "${RUFF_OPTS[@]}" "${DEFAULT_DIRS[@]}"
        fi
        ;;
esac

# Final status
if [[ $EXIT_CODE -eq 0 ]]; then
    log_info "Ruff completed successfully!"
else
    log_error "Ruff completed with issues."
fi

exit $EXIT_CODE