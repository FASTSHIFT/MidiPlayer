/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - Platform Abstraction Interface
 *
 * Users must implement these functions for their target platform.
 */
#ifndef MP_PORT_H
#define MP_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief  Write a mixed audio sample to the audio output
 * @param  value: 10-bit sample value (0 ~ 1023)
 *         For PWM output: write to TIMx->CCRy
 *         For DAC output: write to DAC register
 *         For host testing: store in buffer
 */
void mp_port_audio_write(uint16_t value);

/**
 * @brief  Get current system tick in milliseconds
 * @retval Millisecond counter (wraps around)
 */
uint32_t mp_port_get_tick_ms(void);

#ifdef __cplusplus
}
#endif

#endif /* MP_PORT_H */
