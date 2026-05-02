# MidiPlayer - Cross-platform MIDI square wave mixer library
#
# Build modes:
#   Host (default): library + unit tests
#   STM32: see examples/stm32f103/CMakeLists.txt

cmake_minimum_required(VERSION 3.16)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

project(MidiPlayer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Include library definition
include(${CMAKE_CURRENT_LIST_DIR}/cmake/library.cmake)

# Build as static library for host
add_library(midiplayer STATIC ${MIDIPLAYER_SOURCES})
target_include_directories(midiplayer PUBLIC ${MIDIPLAYER_INCLUDES})
target_compile_definitions(midiplayer PUBLIC ${MIDIPLAYER_DEFINITIONS})
target_compile_options(midiplayer PRIVATE -Wall -Wextra -Werror)

# Enable testing
enable_testing()
add_subdirectory(tests)
