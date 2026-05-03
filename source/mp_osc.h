/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - Oscillator / Mixer
 *
 * Multi-channel synthesizer with square, triangle, sawtooth waveforms
 * and LFSR noise. Platform-independent pure C.
 */
#ifndef MP_OSC_H
#define MP_OSC_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Configurable channel count (default 8: 7 melodic + 1 noise) */
#ifndef MP_OSC_CH_COUNT
#define MP_OSC_CH_COUNT 8
#endif

/* Audio parameters */
#define MP_OSC_SAMPLE_RATE 16000
#define MP_OSC_PWM_BITS 10
#define MP_OSC_DC_OFFSET (1 << (MP_OSC_PWM_BITS - 1)) /* 512 */
#define MP_OSC_MAX_VOLUME 127
#define MP_OSC_MOD_DEFAULT 0x7F /* 50% duty cycle (square wave) */

/* ISR prescaler: tick handler runs at SAMPLE_RATE / PRESCALER_DIV */
#define MP_OSC_PRESCALER_DIV 8

/* Noise channel is always the last channel */
#define MP_OSC_NOISE_CH (MP_OSC_CH_COUNT - 1)

/* Waveform types for melodic channels */
typedef enum {
    MP_WAVE_SQUARE = 0, /* Classic square wave (duty cycle via mod) */
    MP_WAVE_TRIANGLE,   /* Triangle wave (soft, flute-like) */
    MP_WAVE_SAWTOOTH,   /* Sawtooth wave (rich harmonics, string-like) */
    MP_WAVE_PULSE_25,   /* Fixed 25% pulse (bright, thin) */
    MP_WAVE_COUNT,
} mp_waveform_t;

/* Per-channel oscillator parameters */
struct mp_osc_params {
    uint8_t mod;              /* Duty cycle modulation (0~255, 127=50%) */
    uint8_t vol;              /* Volume (0~127) */
    uint16_t phase_increment; /* Frequency control word */
    uint8_t waveform;         /* Waveform type (mp_waveform_t) */
};

/**
 * @brief  Initialize oscillator state
 */
void mp_osc_init(void);

/**
 * @brief  Generate one mixed audio sample from all channels
 * @retval 10-bit sample value (0 ~ 1023)
 * @note   Call this at MP_OSC_SAMPLE_RATE (16kHz) from timer ISR
 */
uint16_t mp_osc_mix_sample(void);

/**
 * @brief  Get direct access to channel parameters
 * @param  ch: channel index (0 ~ MP_OSC_CH_COUNT-1)
 * @retval Pointer to channel params, or NULL if ch is invalid
 */
struct mp_osc_params* mp_osc_get_params(uint8_t ch);

/**
 * @brief  Set channel frequency via phase increment
 */
void mp_osc_set_freq(uint8_t ch, uint16_t phase_inc);

/**
 * @brief  Set channel volume (0 ~ 127)
 */
void mp_osc_set_vol(uint8_t ch, uint8_t vol);

/**
 * @brief  Set channel duty cycle modulation (0~255, 127=50%)
 */
void mp_osc_set_mod(uint8_t ch, uint8_t mod);

/**
 * @brief  Set channel waveform type
 */
void mp_osc_set_waveform(uint8_t ch, mp_waveform_t waveform);

/**
 * @brief  Silence all channels
 */
void mp_osc_silence(void);

#ifdef __cplusplus
}
#endif

#endif /* MP_OSC_H */
