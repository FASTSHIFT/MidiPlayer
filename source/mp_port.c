/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - Platform Abstraction Implementation
 */
#include "mp_port.h"
#include <string.h>

static mp_port_t mp_port_callbacks;

void mp_port_init(const mp_port_t* port) {
    if (port) {
        mp_port_callbacks = *port;
    } else {
        memset(&mp_port_callbacks, 0, sizeof(mp_port_callbacks));
    }
}

void mp_port_audio_write(uint16_t value) {
    if (mp_port_callbacks.audio_write) {
        mp_port_callbacks.audio_write(value);
    }
}

uint32_t mp_port_get_tick_ms(void) {
    if (mp_port_callbacks.get_tick_ms) {
        return mp_port_callbacks.get_tick_ms();
    }
    return 0;
}
