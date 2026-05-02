/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - Platform Abstraction Interface (Callback-based)
 *
 * Users register platform callbacks via mp_port_init() instead of
 * implementing fixed function names. This allows dynamic switching
 * and avoids link-time coupling.
 */
#ifndef MP_PORT_H
#define MP_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief  Audio output callback type
 * @param  value: 10-bit sample value (0 ~ 1023)
 */
typedef void (*mp_audio_write_cb)(uint16_t value);

/**
 * @brief  Tick callback type
 * @retval Current system time in milliseconds
 */
typedef uint32_t (*mp_get_tick_cb)(void);

/**
 * @brief  Platform callbacks
 */
typedef struct {
    mp_audio_write_cb audio_write; /* Write mixed sample to output */
    mp_get_tick_cb get_tick_ms;    /* Get current time in ms */
} mp_port_t;

/**
 * @brief  Register platform callbacks
 * @param  port: pointer to callback struct (contents are copied)
 * @note   Must be called before mp_init()
 */
void mp_port_init(const mp_port_t* port);

/**
 * @brief  Write audio sample via registered callback
 */
void mp_port_audio_write(uint16_t value);

/**
 * @brief  Get tick via registered callback
 */
uint32_t mp_port_get_tick_ms(void);

#ifdef __cplusplus
}
#endif

#endif /* MP_PORT_H */
