#!/bin/bash
#
# load_midi.sh - Convert a MIDI file and flash it to STM32
#
# Usage:
#   ./tools/load_midi.sh <file.mid> [options]
#
# Options:
#   -t, --tracks N     Max tracks to include (default: 3)
#   -p, --probe TYPE   Flash probe: stlink or daplink (default: daplink)
#   -n, --no-flash     Convert and build only, don't flash
#   -h, --help         Show help
#
# Examples:
#   ./tools/load_midi.sh resources/BeatIt.mid
#   ./tools/load_midi.sh resources/BeatIt.mid -t 5
#   ./tools/load_midi.sh resources/BeatIt.mid -p stlink
#   ./tools/load_midi.sh resources/BeatIt.mid -n

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EXAMPLE_DIR="$PROJECT_ROOT/examples/stm32f103"
BUILD_DIR="$EXAMPLE_DIR/build"
CONVERTER="$PROJECT_ROOT/tools/midi_to_header.py"
FLASH_SCRIPT="$SCRIPT_DIR/flash.sh"

MAX_TRACKS=7
PROBE="daplink"
DO_FLASH=1
MIDI_FILE=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    cat <<EOF
Usage: $0 <file.mid> [options]

Convert a MIDI file to C header, build STM32 firmware, and flash it.

Options:
  -t, --tracks N     Max tracks to include (default: 3)
  -p, --probe TYPE   Flash probe: stlink or daplink (default: daplink)
  -n, --no-flash     Convert and build only, don't flash
  -h, --help         Show help
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t | --tracks) MAX_TRACKS="$2"; shift 2 ;;
        -p | --probe) PROBE="$2"; shift 2 ;;
        -n | --no-flash) DO_FLASH=0; shift ;;
        -h | --help) show_help; exit 0 ;;
        -*) echo -e "${RED}Unknown option: $1${NC}"; show_help; exit 1 ;;
        *) MIDI_FILE="$1"; shift ;;
    esac
done

if [ -z "$MIDI_FILE" ]; then
    echo -e "${RED}Error: No MIDI file specified${NC}"
    show_help
    exit 1
fi

if [ ! -f "$MIDI_FILE" ]; then
    echo -e "${RED}Error: File not found: $MIDI_FILE${NC}"
    exit 1
fi

MIDI_NAME=$(basename "$MIDI_FILE" .mid)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MidiPlayer - Load MIDI to STM32${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}File:${NC}   $MIDI_FILE"
echo -e "${YELLOW}Tracks:${NC} $MAX_TRACKS"
echo ""

# Step 1: Convert MIDI to header
echo -e "${YELLOW}[1/3] Converting MIDI...${NC}"
python3 "$CONVERTER" "$MIDI_FILE" "$EXAMPLE_DIR/midi_data.h" \
    --name midi_score --max-tracks "$MAX_TRACKS"
echo ""

# Step 2: Build firmware
echo -e "${YELLOW}[2/3] Building firmware...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
(
    cd "$BUILD_DIR"
    cmake -DCMAKE_TOOLCHAIN_FILE="$PROJECT_ROOT/cmake/arm-none-eabi-gcc.cmake" .. 2>&1
    make -j"$(nproc)" 2>&1
) | tail -5
echo ""

# Step 3: Flash
if [ $DO_FLASH -eq 1 ]; then
    echo -e "${YELLOW}[3/3] Flashing...${NC}"
    "$FLASH_SCRIPT" -p "$PROBE" -r "$BUILD_DIR/MidiPlayer_STM32.hex"
else
    echo -e "${YELLOW}[3/3] Skipping flash (--no-flash)${NC}"
    echo -e "  Firmware: $BUILD_DIR/MidiPlayer_STM32.hex"
fi

echo ""
echo -e "${GREEN}Done! Now playing: $MIDI_NAME${NC}"
