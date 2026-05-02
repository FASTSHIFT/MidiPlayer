/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - Public API
 *
 * Unified interface combining oscillator and sequencer.
 */
#ifndef MP_PLAYER_H
#define MP_PLAYER_H

#include "mp_osc.h"
#include "mp_sequencer.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief  Initialize the MidiPlayer library
 *         Must be called before any other mp_* functions.
 */
void mp_init(void);

/**
 * @brief  Start playing a score
 * @param  score: pointer to score descriptor
 */
void mp_play(const mp_score_t* score);

/**
 * @brief  Stop playback and silence all channels
 */
void mp_stop(void);

/**
 * @brief  Check if playback is active
 * @retval 1 if playing, 0 if stopped
 */
uint8_t mp_is_playing(void);

/**
 * @brief  Audio sample tick - call from timer ISR at 16kHz
 * @retval 10-bit mixed audio sample (0~1023)
 *
 * Typical usage in timer ISR:
 *   uint16_t sample = mp_audio_tick();
 *   mp_port_audio_write(sample);
 */
uint16_t mp_audio_tick(void);

/**
 * @brief  Sequencer tick - call periodically with current time
 * @param  current_ms: current time in milliseconds
 */
void mp_update(uint32_t current_ms);

/**
 * @brief  Get elapsed playback time in milliseconds
 */
uint32_t mp_get_elapsed_ms(void);

/**
 * @brief  Get total score duration in milliseconds
 */
uint32_t mp_get_total_ms(void);

/**
 * @brief  Get playback progress as percentage (0~100)
 */
uint8_t mp_get_progress_pct(void);

#ifdef __cplusplus
}
#endif

#endif /* MP_PLAYER_H */
