/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Test helpers for MidiPlayer host-based testing
 */
#include "mock_port.h"
#include <string.h>

static uint16_t mock_audio_buffer[MOCK_AUDIO_BUFFER_SIZE];
static uint32_t mock_audio_index = 0;

uint16_t* mock_port_get_audio_buffer(void) {
    return mock_audio_buffer;
}

uint32_t mock_port_get_audio_count(void) {
    return mock_audio_index;
}

void mock_port_reset(void) {
    memset(mock_audio_buffer, 0, sizeof(mock_audio_buffer));
    mock_audio_index = 0;
}

void mock_port_record_sample(uint16_t sample) {
    if (mock_audio_index < MOCK_AUDIO_BUFFER_SIZE) {
        mock_audio_buffer[mock_audio_index++] = sample;
    }
}
