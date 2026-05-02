# MidiPlayer Unit Tests
# Host-based testing with coverage support

cmake_minimum_required(VERSION 3.16)

# Coverage option
option(COVERAGE "Enable coverage reporting" ON)
option(ASAN "Enable AddressSanitizer" ON)

if(COVERAGE)
  set(CMAKE_C_FLAGS
      "${CMAKE_C_FLAGS} -g -O0 --coverage -fprofile-arcs -ftest-coverage")
  set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} --coverage")
endif()

if(ASAN)
  set(CMAKE_C_FLAGS
      "${CMAKE_C_FLAGS} -fsanitize=address -fno-omit-frame-pointer -g")
  set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fsanitize=address")
endif()

# Source under test
set(SUT_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/../source/mp_osc.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../source/mp_note_table.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../source/mp_sequencer.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../source/mp_player.c)

# Mock and framework sources
set(MOCK_SOURCES mock_port.c)

set(TEST_FRAMEWORK_SOURCES test_framework.c)

# Test sources
set(TEST_SOURCES test_main.c test_osc.c test_note_table.c test_sequencer.c
                 test_player.c)

# Test executable
add_executable(
  test_runner ${SUT_SOURCES} ${MOCK_SOURCES} ${TEST_FRAMEWORK_SOURCES}
              ${TEST_SOURCES})

target_include_directories(
  test_runner PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}
                      ${CMAKE_CURRENT_SOURCE_DIR}/../source)

target_compile_options(test_runner PRIVATE -Wall -Wextra -Werror)

# CTest integration
add_test(NAME midiplayer_tests COMMAND test_runner)
