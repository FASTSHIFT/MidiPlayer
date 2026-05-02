#!/bin/bash
#
# CMake format/check script for MidiPlayer project
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if ! command -v cmake-format &>/dev/null; then
    echo "Error: cmake-format not installed. Install with: pip install cmake-format"
    exit 1
fi

CMAKE_FILES=$(find "$PROJECT_ROOT" \
    -type d \( -name 'build' -o -name 'build_test' \) -prune -o \
    \( -name 'CMakeLists.txt' -o -name '*.cmake' \) -print)

CHECK_MODE=false
if [[ "$1" == "--check" ]]; then
    CHECK_MODE=true
    echo "Running in check mode (no changes will be made)"
fi

FAILED=0
for file in $CMAKE_FILES; do
    if $CHECK_MODE; then
        if ! cmake-format --check "$file" 2>/dev/null; then
            echo "[NEEDS FORMAT] $file"
            FAILED=1
        else
            echo "[OK] $file"
        fi
    else
        cmake-format -i "$file"
        echo "[FORMATTED] $file"
    fi
done

if $CHECK_MODE && [[ $FAILED -ne 0 ]]; then
    echo "Some CMake files need formatting. Run without --check to fix."
    exit 1
fi

exit 0
