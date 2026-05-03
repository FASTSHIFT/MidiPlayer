/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - Public API
 *
 * Unified interface combining oscillator and sequencer.
 * Platform code calls mp_audio_tick() and mp_update() directly.
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
 * @brief  Generate one mixed audio sample
 * @retval 10-bit sample (0~1023), write this to your PWM/DAC
 * @note   Call at 16kHz from timer ISR
 */
uint16_t mp_audio_tick(void);

/**
 * @brief  Advance the sequencer
 * @param  current_ms: current time in milliseconds
 * @note   Call at 2kHz (e.g. every 8th call of the 16kHz ISR)
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
