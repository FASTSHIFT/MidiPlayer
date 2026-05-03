#!/bin/bash

# MIT License
# Copyright (c) 2025 - 2026 _VIFEXTech

# Auto-format script for MidiPlayer Python tools
# Formats all Python files, supports --check and --lint modes
# Based on FPBInject WebServer format.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  MidiPlayer Python Formatter${NC}"
echo -e "${BLUE}================================================${NC}"

# Common exclude patterns for find
FIND_EXCLUDE_COMMON=(
    -not -path "./__pycache__/*"
    -not -path "*/__pycache__/*"
    -not -path "./htmlcov/*"
    -not -path "./coverage/*"
    -not -path "./tests/htmlcov/*"
    -not -path "./tests/coverage/*"
    -not -path "./.venv/*"
    -not -path "./venv/*"
    -not -name "midi_player_legacy.py"
)

# ============================================================
# Format / Lint functions
# ============================================================

format_python() {
    echo -e "\n${GREEN}📦 Formatting Python files (*.py)...${NC}"

    if python3 -m black --version &>/dev/null; then
        echo -e "   Using $(python3 -m black --version)"
    else
        echo -e "${YELLOW}   Installing black...${NC}"
        pip install black -q
    fi

    local files=$(find . -name "*.py" \
        "${FIND_EXCLUDE_COMMON[@]}" \
        2>/dev/null | sort)

    if [ -z "$files" ]; then
        echo "   No Python files found"
        return 0
    fi

    local count=$(echo "$files" | wc -l)

    if [ "$CHECK_ONLY" = true ]; then
        if python3 -m black --check --quiet --line-length 88 $files 2>&1; then
            echo -e "   ${GREEN}Python: $count file(s) properly formatted ✓${NC}"
            return 0
        else
            echo -e "   ${RED}Python: some files need formatting ✗${NC}"
            echo -e "   Run: tools/python_format.sh"
            return 1
        fi
    else
        if python3 -m black --quiet --line-length 88 $files 2>&1; then
            echo -e "   ${GREEN}Python: $count file(s) formatted ✓${NC}"
            return 0
        else
            echo -e "   ${RED}Python: black failed ✗${NC}"
            return 1
        fi
    fi
}

lint_python() {
    echo -e "\n${GREEN}📦 Linting Python files...${NC}"

    if ! python3 -m flake8 --version &>/dev/null; then
        echo -e "${YELLOW}   Installing flake8...${NC}"
        pip install flake8 -q
    fi

    local files=$(find . -name "*.py" \
        "${FIND_EXCLUDE_COMMON[@]}" \
        2>/dev/null | sort)

    if [ -z "$files" ]; then
        echo "   No Python files found"
        return 0
    fi

    # Split into test and non-test files for different ignore rules
    local test_files=""
    local src_files=""
    for file in $files; do
        if [[ "$file" == *"/tests/"* ]]; then
            test_files="$test_files $file"
        else
            src_files="$src_files $file"
        fi
    done

    local lint_errors=0

    if [ -n "$src_files" ]; then
        if ! python3 -m flake8 --ignore=E501,W503,E203 --max-line-length=120 $src_files 2>/dev/null; then
            lint_errors=$((lint_errors + 1))
        fi
    fi

    if [ -n "$test_files" ]; then
        if ! python3 -m flake8 --ignore=E501,W503,E203,E402 --max-line-length=120 $test_files 2>/dev/null; then
            lint_errors=$((lint_errors + 1))
        fi
    fi

    if [ $lint_errors -eq 0 ]; then
        echo -e "   ${GREEN}All Python files passed linting ✓${NC}"
        return 0
    else
        echo -e "   ${YELLOW}$lint_errors category(s) have linting warnings${NC}"
        return 1
    fi
}

# ============================================================
# Parse arguments
# ============================================================
CHECK_ONLY=false
LINT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --check | -c)
            CHECK_ONLY=true
            shift
            ;;
        --lint | -l)
            LINT=true
            shift
            ;;
        --help | -h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --check, -c    Check formatting without making changes"
            echo "  --lint, -l     Run linting after formatting"
            echo "  --help, -h     Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ "$CHECK_ONLY" = true ]; then
    echo -e "${YELLOW}Running in check-only mode...${NC}"
fi

# ============================================================
# Run
# ============================================================

FAILED=0

format_python || FAILED=1

if [ "$LINT" = true ]; then
    lint_python || FAILED=1
fi

echo -e "\n${BLUE}================================================${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed!${NC}"
    exit 1
fi
