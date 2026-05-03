/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - ADSR Envelope Generator
 *
 * Simple linear ADSR envelope that modulates channel volume.
 * Runs at sequencer tick rate (2kHz by default).
 *
 * Envelope stages:
 *   IDLE    -> note_on  -> ATTACK
 *   ATTACK  -> peak     -> DECAY
 *   DECAY   -> sustain  -> SUSTAIN
 *   SUSTAIN -> note_off -> RELEASE
 *   RELEASE -> zero     -> IDLE
 */
#ifndef MP_ENVELOPE_H
#define MP_ENVELOPE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef MP_OSC_CH_COUNT
#define MP_OSC_CH_COUNT 4
#endif

/* Envelope stage */
typedef enum {
    MP_ENV_IDLE = 0,
    MP_ENV_ATTACK,
    MP_ENV_DECAY,
    MP_ENV_SUSTAIN,
    MP_ENV_RELEASE,
} mp_env_stage_t;

/* ADSR parameters (times in ticks at 2kHz, so 1 tick = 0.5ms) */
typedef struct {
    uint16_t attack;  /* Ticks to ramp from 0 to peak (0 = instant) */
    uint16_t decay;   /* Ticks to ramp from peak to sustain level */
    uint8_t sustain;  /* Sustain level (0~255, fraction of peak: 255=100%) */
    uint16_t release; /* Ticks to ramp from sustain to 0 */
} mp_adsr_params_t;

/* Per-channel envelope state */
typedef struct {
    mp_env_stage_t stage;
    uint16_t counter;    /* Ticks remaining in current stage */
    uint8_t level;       /* Current envelope level (0~255) */
    uint8_t peak_vol;    /* Note velocity (target for attack) */
    uint8_t sustain_vol; /* Computed sustain volume */
} mp_env_state_t;

/* Preset ADSR profiles for different instrument families */
typedef enum {
    MP_ADSR_PRESET_DEFAULT = 0, /* General purpose */
    MP_ADSR_PRESET_PIANO,       /* Fast attack, long decay */
    MP_ADSR_PRESET_ORGAN,       /* Instant attack, full sustain */
    MP_ADSR_PRESET_STRINGS,     /* Slow attack, full sustain */
    MP_ADSR_PRESET_BASS,        /* Fast attack, medium decay */
    MP_ADSR_PRESET_LEAD,        /* Fast attack, high sustain */
    MP_ADSR_PRESET_PAD,         /* Slow attack, slow release */
    MP_ADSR_PRESET_PERCUSSION,  /* Instant attack, fast decay, no sustain */
    MP_ADSR_PRESET_COUNT,
} mp_adsr_preset_t;

/**
 * @brief  Initialize all envelope states to idle
 */
void mp_env_init(void);

/**
 * @brief  Set ADSR parameters for a channel
 * @param  ch: channel index
 * @param  params: ADSR parameters
 */
void mp_env_set_adsr(uint8_t ch, const mp_adsr_params_t* params);

/**
 * @brief  Load a preset ADSR profile for a channel
 * @param  ch: channel index
 * @param  preset: preset identifier
 */
void mp_env_set_preset(uint8_t ch, mp_adsr_preset_t preset);

/**
 * @brief  Trigger note-on (start attack phase)
 * @param  ch: channel index
 * @param  velocity: note velocity (0~127), used as peak volume
 */
void mp_env_note_on(uint8_t ch, uint8_t velocity);

/**
 * @brief  Trigger note-off (start release phase)
 * @param  ch: channel index
 */
void mp_env_note_off(uint8_t ch);

/**
 * @brief  Process one envelope tick for all channels
 * @note   Call at 2kHz (from sequencer prescaler)
 *
 * Updates envelope levels and writes modulated volume to oscillator.
 */
void mp_env_tick(void);

/**
 * @brief  Get current envelope level for a channel
 * @param  ch: channel index
 * @retval Envelope level (0~255)
 */
uint8_t mp_env_get_level(uint8_t ch);

/**
 * @brief  Get ADSR preset parameters
 * @param  preset: preset identifier
 * @retval Pointer to preset params, or NULL if invalid
 */
const mp_adsr_params_t* mp_env_get_preset_params(mp_adsr_preset_t preset);

#ifdef __cplusplus
}
#endif

#endif /* MP_ENVELOPE_H */
