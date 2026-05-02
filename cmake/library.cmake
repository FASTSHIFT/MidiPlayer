# MidiPlayer Library Integration Module
#
# Usage: include this file from your project's CMakeLists.txt
#
# Provides:
#   MIDIPLAYER_SOURCES     - Source files to compile
#   MIDIPLAYER_INCLUDES    - Include directories
#   MIDIPLAYER_DEFINITIONS - Compile definitions
#
# Options (set before including):
#   MP_OSC_CH_COUNT - Number of oscillator channels (default: 4)

# Resolve MidiPlayer root directory
get_filename_component(MIDIPLAYER_ROOT "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)

# Validate
if(NOT EXISTS "${MIDIPLAYER_ROOT}/source/mp_osc.c")
  message(FATAL_ERROR "MidiPlayer: Source not found at ${MIDIPLAYER_ROOT}")
endif()

# Source files
set(MIDIPLAYER_SOURCES
    ${MIDIPLAYER_ROOT}/source/mp_port.c
    ${MIDIPLAYER_ROOT}/source/mp_osc.c
    ${MIDIPLAYER_ROOT}/source/mp_envelope.c
    ${MIDIPLAYER_ROOT}/source/mp_note_table.c
    ${MIDIPLAYER_ROOT}/source/mp_sequencer.c
    ${MIDIPLAYER_ROOT}/source/mp_player.c)

# Include directories
set(MIDIPLAYER_INCLUDES ${MIDIPLAYER_ROOT}/source)

# Compile definitions
set(MIDIPLAYER_DEFINITIONS "")

if(DEFINED MP_OSC_CH_COUNT)
  list(APPEND MIDIPLAYER_DEFINITIONS MP_OSC_CH_COUNT=${MP_OSC_CH_COUNT})
endif()

message(STATUS "MidiPlayer: Enabled (${MP_OSC_CH_COUNT} channels)")
