#!/bin/bash
#
# setup_env.sh — Install all MidiPlayer development dependencies
#
# Usage:
#   tools/setup_env.sh           # Install everything (Python + system)
#   tools/setup_env.sh --python  # Python dependencies only (for CI)
#   tools/setup_env.sh --stm32   # ARM toolchain only
#   tools/setup_env.sh --ci      # CI mode: Python dev deps, no system packages
#
# System packages require sudo. Python packages install to user site.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Defaults: install everything
INSTALL_PYTHON=true
INSTALL_STM32=true
INSTALL_SYSTEM=true
DEV_MODE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --python)
            INSTALL_STM32=false
            INSTALL_SYSTEM=false
            shift
            ;;
        --stm32)
            INSTALL_PYTHON=false
            INSTALL_SYSTEM=false
            shift
            ;;
        --ci)
            # CI: only Python dev deps, no sudo
            INSTALL_STM32=false
            INSTALL_SYSTEM=false
            DEV_MODE=true
            shift
            ;;
        -h | --help)
            echo "Usage: $0 [--python | --stm32 | --ci]"
            echo ""
            echo "Options:"
            echo "  (none)     Install everything (Python + system + ARM toolchain)"
            echo "  --python   Python dependencies only"
            echo "  --stm32    ARM toolchain only"
            echo "  --ci       Python dev dependencies only (no sudo)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MidiPlayer Environment Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# ── System packages (apt) ──────────────────────────────────────────

if $INSTALL_SYSTEM; then
    echo -e "\n${GREEN}📦 Installing system packages...${NC}"
    sudo apt-get update -qq
    sudo apt-get install -y \
        python3-tk \
        portaudio19-dev \
        clang-format-14 \
        lcov bc
    echo -e "   ${GREEN}System packages installed ✓${NC}"
fi

# ── ARM toolchain ──────────────────────────────────────────────────

if $INSTALL_STM32; then
    echo -e "\n${GREEN}📦 Installing ARM toolchain...${NC}"
    sudo apt-get update -qq
    sudo apt-get install -y gcc-arm-none-eabi
    echo -e "   ${GREEN}ARM toolchain installed ✓${NC}"
fi

# ── Python dependencies ───────────────────────────────────────────

if $INSTALL_PYTHON; then
    echo -e "\n${GREEN}📦 Installing Python dependencies...${NC}"

    # pyaudio requires portaudio19-dev at build time; install it if missing
    if ! dpkg -s portaudio19-dev &>/dev/null; then
        echo -e "   ${YELLOW}portaudio19-dev not found, installing (required by pyaudio)...${NC}"
        sudo apt-get update -qq
        sudo apt-get install -y portaudio19-dev
    fi

    if $DEV_MODE; then
        pip install -r "$SCRIPT_DIR/requirements-dev.txt"
        echo -e "   ${GREEN}Python dev dependencies installed ✓${NC}"
    else
        pip install -r "$SCRIPT_DIR/requirements.txt"
        echo -e "   ${GREEN}Python runtime dependencies installed ✓${NC}"
    fi
fi

# ── Summary ───────────────────────────────────────────────────────

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Setup complete!${NC}"

if $INSTALL_PYTHON; then
    echo -e "   Python: $(python3 --version 2>&1)"
fi
if $INSTALL_STM32; then
    echo -e "   ARM GCC: $(arm-none-eabi-gcc --version 2>&1 | head -1)"
fi
