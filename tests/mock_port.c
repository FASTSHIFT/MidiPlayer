/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Mock implementation of mp_port.h for host-based testing
 */
#include "mock_port.h"
#include "mp_port.h"
#include <string.h>

static uint16_t mock_audio_buffer[MOCK_AUDIO_BUFFER_SIZE];
static uint32_t mock_audio_index = 0;
static uint32_t mock_tick_ms = 0;

/* mp_port.h interface implementation */

void mp_port_audio_write(uint16_t value) {
    if (mock_audio_index < MOCK_AUDIO_BUFFER_SIZE) {
        mock_audio_buffer[mock_audio_index++] = value;
    }
}

uint32_t mp_port_get_tick_ms(void) {
    return mock_tick_ms;
}

/* Test helpers */

uint16_t* mock_port_get_audio_buffer(void) {
    return mock_audio_buffer;
}

uint32_t mock_port_get_audio_count(void) {
    return mock_audio_index;
}

uint32_t mock_port_get_tick(void) {
    return mock_tick_ms;
}

void mock_port_reset(void) {
    memset(mock_audio_buffer, 0, sizeof(mock_audio_buffer));
    mock_audio_index = 0;
    mock_tick_ms = 0;
}

void mock_port_set_tick(uint32_t ms) {
    mock_tick_ms = ms;
}

void mock_port_advance_tick(uint32_t ms) {
    mock_tick_ms += ms;
}
