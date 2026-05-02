# MidiPlayer STM32F103 Example
# Standalone build: plays MIDI through PWM audio output

cmake_minimum_required(VERSION 3.16)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

project(MidiPlayer_STM32 C CXX ASM)

# STM32F103C8T6 (Medium Density, 64KB Flash, 20KB RAM)
set(STM32_DEVICE
    "STM32F10X_MD"
    CACHE STRING "STM32 Device type")
set(HSE_VALUE
    "8000000"
    CACHE STRING "HSE crystal frequency")

add_compile_definitions(${STM32_DEVICE} USE_STDPERIPH_DRIVER
                        HSE_VALUE=${HSE_VALUE} ARDUINO=111)

# MidiPlayer root
get_filename_component(MP_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)

# Include MidiPlayer library
include(${MP_ROOT}/cmake/library.cmake)

# Platform directories
set(PLATFORM_DIR ${CMAKE_CURRENT_LIST_DIR}/platform/stm32f10x)
set(ARDUINO_DIR ${PLATFORM_DIR}/ArduinoAPI)

# Linker script
set(LINKER_SCRIPT ${PLATFORM_DIR}/Startup/STM32F103C8_FLASH.ld)

# Platform sources
file(GLOB PLATFORM_CORE_SOURCES ${PLATFORM_DIR}/Core/*.c
     ${PLATFORM_DIR}/Core/*.cpp)
file(GLOB CMSIS_DEVICE_SOURCES ${PLATFORM_DIR}/CMSIS/Device/*.c)
file(GLOB STDPERIPH_SOURCES
     ${PLATFORM_DIR}/STM32F10x_StdPeriph_Driver/Src/*.c)
file(GLOB ARDUINO_SOURCES ${ARDUINO_DIR}/*.c ${ARDUINO_DIR}/*.cpp)
set(STARTUP_SOURCE ${PLATFORM_DIR}/Startup/startup_stm32f10x.s)

# Application sources
set(APP_SOURCES ${CMAKE_CURRENT_LIST_DIR}/main.cpp
                ${CMAKE_CURRENT_LIST_DIR}/port_stm32f103.c)

# All sources
set(ALL_SOURCES
    ${MIDIPLAYER_SOURCES}
    ${APP_SOURCES}
    ${ARDUINO_SOURCES}
    ${PLATFORM_CORE_SOURCES}
    ${CMSIS_DEVICE_SOURCES}
    ${STDPERIPH_SOURCES}
    ${STARTUP_SOURCE})

# Include directories
set(INCLUDE_DIRS
    ${MIDIPLAYER_INCLUDES}
    ${CMAKE_CURRENT_LIST_DIR}
    ${ARDUINO_DIR}
    ${ARDUINO_DIR}/avr
    ${PLATFORM_DIR}/Config
    ${PLATFORM_DIR}/Core
    ${PLATFORM_DIR}/CMSIS/Include
    ${PLATFORM_DIR}/CMSIS/Device
    ${PLATFORM_DIR}/STM32F10x_StdPeriph_Driver/Inc)

# Create executable
add_executable(${PROJECT_NAME} ${ALL_SOURCES})
set_target_properties(${PROJECT_NAME} PROPERTIES SUFFIX ".elf")
target_include_directories(${PROJECT_NAME} PRIVATE ${INCLUDE_DIRS})
target_compile_definitions(${PROJECT_NAME} PRIVATE ${MIDIPLAYER_DEFINITIONS})
target_link_options(
  ${PROJECT_NAME} PRIVATE -T${LINKER_SCRIPT}
  -Wl,-Map=${CMAKE_BINARY_DIR}/${PROJECT_NAME}.map,--cref)

# Generate HEX and BIN
add_custom_command(
  TARGET ${PROJECT_NAME}
  POST_BUILD
  COMMAND ${CMAKE_OBJCOPY} -O ihex ${CMAKE_BINARY_DIR}/${PROJECT_NAME}.elf
          ${CMAKE_BINARY_DIR}/${PROJECT_NAME}.hex
  COMMAND ${CMAKE_OBJCOPY} -O binary ${CMAKE_BINARY_DIR}/${PROJECT_NAME}.elf
          ${CMAKE_BINARY_DIR}/${PROJECT_NAME}.bin
  COMMAND ${CMAKE_SIZE} ${CMAKE_BINARY_DIR}/${PROJECT_NAME}.elf
  COMMENT "Generating HEX and BIN files...")

message(STATUS "========================================")
message(STATUS "MidiPlayer STM32F103 Example")
message(STATUS "========================================")
message(STATUS "Device: ${STM32_DEVICE}")
message(STATUS "HSE: ${HSE_VALUE} Hz")
message(STATUS "Linker Script: ${LINKER_SCRIPT}")
message(STATUS "========================================")
