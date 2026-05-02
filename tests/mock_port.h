/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Mock implementation of mp_port.h for host-based testing
 */
#ifndef MOCK_PORT_H
#define MOCK_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MOCK_AUDIO_BUFFER_SIZE 8192

/* Access mock state for test assertions */
uint16_t* mock_port_get_audio_buffer(void);
uint32_t mock_port_get_audio_count(void);
uint32_t mock_port_get_tick(void);

/* Test helpers */
void mock_port_reset(void);
void mock_port_set_tick(uint32_t ms);
void mock_port_advance_tick(uint32_t ms);

/* Register mock callbacks with mp_port_init() */
void mock_port_install(void);

#ifdef __cplusplus
}
#endif

#endif /* MOCK_PORT_H */
