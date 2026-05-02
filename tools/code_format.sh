#!/bin/bash
#
# Auto format script for MidiPlayer project
# Formats C/C++ files in source/, tests/, and examples/ directories
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Prefer clang-format-14 if available
if command -v clang-format-14 &>/dev/null; then
    CLANG_FORMAT=clang-format-14
elif command -v clang-format &>/dev/null; then
    CLANG_FORMAT=clang-format
else
    echo "Error: clang-format is not installed"
    echo "Install it with: sudo apt install clang-format-14"
    exit 1
fi

echo "Using clang-format: $CLANG_FORMAT"
echo "Version: $($CLANG_FORMAT --version)"

# Directories to format
FORMAT_DIRS=(
    "$PROJECT_ROOT/source"
    "$PROJECT_ROOT/tests"
    "$PROJECT_ROOT/examples"
)

EXTENSIONS=("*.c" "*.cpp" "*.h" "*.hpp")

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "MidiPlayer Code Formatter"
echo "========================================="
echo ""

CHECK_MODE=false
if [[ "$1" == "--check" ]]; then
    CHECK_MODE=true
    echo -e "${YELLOW}Running in check mode (no changes will be made)${NC}"
    echo ""
fi

TOTAL_FILES=0
FORMATTED_FILES=0
FAILED_FILES=0

for dir in "${FORMAT_DIRS[@]}"; do
    if [[ ! -d "$dir" ]]; then
        continue
    fi

    echo "Processing: $dir"

    for ext in "${EXTENSIONS[@]}"; do
        while IFS= read -r -d '' file; do
            # Skip vendor platform files (copied from FPBInject, not ours to format)
            if [[ "$file" == *"/platform/"* ]] ||
                [[ "$file" == *"/build/"* ]]; then
                continue
            fi

            TOTAL_FILES=$((TOTAL_FILES + 1))

            if $CHECK_MODE; then
                if ! $CLANG_FORMAT --dry-run --Werror "$file" 2>/dev/null; then
                    echo -e "  ${RED}[NEEDS FORMAT]${NC} $file"
                    FAILED_FILES=$((FAILED_FILES + 1))
                else
                    echo -e "  ${GREEN}[OK]${NC} $file"
                    FORMATTED_FILES=$((FORMATTED_FILES + 1))
                fi
            else
                if $CLANG_FORMAT -i "$file" 2>/dev/null; then
                    echo -e "  ${GREEN}[FORMATTED]${NC} $file"
                    FORMATTED_FILES=$((FORMATTED_FILES + 1))
                else
                    echo -e "  ${RED}[FAILED]${NC} $file"
                    FAILED_FILES=$((FAILED_FILES + 1))
                fi
            fi
        done < <(find "$dir" -type f -name "$ext" -print0 2>/dev/null)
    done
done

echo ""
echo "========================================="
echo "Summary:"
echo "  Total files:     $TOTAL_FILES"
if $CHECK_MODE; then
    echo "  Properly formatted: $FORMATTED_FILES"
    echo "  Need formatting:    $FAILED_FILES"
else
    echo "  Formatted:       $FORMATTED_FILES"
    echo "  Failed:          $FAILED_FILES"
fi
echo "========================================="

if $CHECK_MODE && [[ $FAILED_FILES -gt 0 ]]; then
    exit 1
fi

exit 0
