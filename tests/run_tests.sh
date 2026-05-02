#!/bin/bash
# MidiPlayer - Build and run unit tests with coverage
#
# Usage:
#   ./run_tests.sh              - Build and run tests
#   ./run_tests.sh coverage     - Build, run, and generate coverage report
#   ./run_tests.sh clean        - Clean build artifacts
#   ./run_tests.sh --threshold N - Set coverage threshold (default: 80%)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"

LINE_THRESHOLD=80
FUNC_THRESHOLD=80

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }

clean_build() {
    print_header "Cleaning build artifacts"
    rm -rf "${BUILD_DIR}"
    print_success "Build directory cleaned"
}

build_tests() {
    print_header "Building tests"
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"
    print_info "Configuring CMake..."
    cmake -DCOVERAGE=ON -DASAN=ON "${SCRIPT_DIR}/.."
    print_info "Building..."
    make -j"$(nproc)" test_runner
    print_success "Build complete"
}

run_tests() {
    print_header "Running tests"
    cd "${BUILD_DIR}"
    ./tests/test_runner
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        print_success "All tests passed"
    else
        print_error "Tests failed (exit code: $EXIT_CODE)"
        exit 1
    fi
}

generate_coverage() {
    print_header "Generating coverage report"
    cd "${BUILD_DIR}"

    if ! command -v lcov &>/dev/null; then
        print_error "lcov not found. Install with: sudo apt-get install lcov"
        exit 1
    fi

    mkdir -p coverage

    GCOV_TOOL="gcov"
    CC_VERSION=$(cc --version | head -1 | grep -oP '\d+' | head -1)
    if command -v "gcov-${CC_VERSION}" &>/dev/null; then
        GCOV_TOOL="gcov-${CC_VERSION}"
    fi
    print_info "Using ${GCOV_TOOL}"

    print_info "Capturing coverage data..."
    lcov --capture --directory . --output-file coverage/coverage.info --gcov-tool "${GCOV_TOOL}" 2>/dev/null || true

    print_info "Filtering coverage data..."
    lcov --remove coverage/coverage.info \
        '/usr/*' \
        '*/tests/*' \
        --output-file coverage/coverage.info --gcov-tool "${GCOV_TOOL}" 2>/dev/null || true

    if command -v genhtml &>/dev/null; then
        print_info "Generating HTML report..."
        genhtml coverage/coverage.info --output-directory coverage/html 2>/dev/null || true
        print_success "Coverage report: ${BUILD_DIR}/coverage/html/index.html"
    fi

    print_info "Coverage summary:"
    COVERAGE_OUTPUT=$(lcov --summary coverage/coverage.info 2>&1)
    echo "$COVERAGE_OUTPUT"

    LINE_COV=$(echo "$COVERAGE_OUTPUT" | grep "lines" | sed 's/.*: \([0-9.]*\)%.*/\1/' | head -1)
    FUNC_COV=$(echo "$COVERAGE_OUTPUT" | grep "functions" | sed 's/.*: \([0-9.]*\)%.*/\1/' | head -1)
    LINE_COV=${LINE_COV:-0}
    FUNC_COV=${FUNC_COV:-0}

    echo ""
    print_info "Line coverage: ${LINE_COV}% (threshold: ${LINE_THRESHOLD}%)"
    print_info "Function coverage: ${FUNC_COV}% (threshold: ${FUNC_THRESHOLD}%)"
    echo ""

    LINE_OK=$(echo "$LINE_COV >= $LINE_THRESHOLD" | bc -l 2>/dev/null || echo "1")
    FUNC_OK=$(echo "$FUNC_COV >= $FUNC_THRESHOLD" | bc -l 2>/dev/null || echo "1")

    if [ "$LINE_OK" = "1" ] && [ "$FUNC_OK" = "1" ]; then
        print_success "Coverage thresholds met!"
        return 0
    else
        print_error "Coverage below threshold!"
        [ "$LINE_OK" = "0" ] && print_error "Line coverage ${LINE_COV}% < ${LINE_THRESHOLD}%"
        [ "$FUNC_OK" = "0" ] && print_error "Function coverage ${FUNC_COV}% < ${FUNC_THRESHOLD}%"
        return 1
    fi
}

# Parse arguments
ACTION=""
while [[ $# -gt 0 ]]; do
    case $1 in
        clean) ACTION="clean"; shift ;;
        coverage) ACTION="coverage"; shift ;;
        build) ACTION="build"; shift ;;
        --threshold) LINE_THRESHOLD="$2"; FUNC_THRESHOLD="$2"; shift 2 ;;
        -h | --help)
            echo "Usage: $0 [action] [options]"
            echo "Actions: (none) coverage build clean"
            echo "Options: --threshold N"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

case "${ACTION}" in
    clean) clean_build ;;
    coverage) clean_build; build_tests; run_tests; generate_coverage ;;
    build) build_tests ;;
    *) build_tests; run_tests ;;
esac
