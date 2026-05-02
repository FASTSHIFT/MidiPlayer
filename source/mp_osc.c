/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - Oscillator / Mixer Implementation
 *
 * Multi-waveform synthesis: square, triangle, sawtooth + LFSR noise.
 * All integer math, no lookup tables. Runs in 16kHz timer ISR.
 *
 * Waveform generation from 8-bit phase (high byte of 16-bit accumulator):
 *
 *   Square:   phase < mod ? +vol : -vol
 *   Triangle: linear ramp 0→peak→0 over one period
 *   Sawtooth: linear ramp from -vol to +vol
 *   Pulse25:  phase < 64 ? +vol : -vol  (fixed 25% duty)
 */
#include "mp_osc.h"
#include <string.h>

/* Channel state */
struct mp_osc_params mp_osc_params_array[MP_OSC_CH_COUNT];
static uint16_t mp_osc_phase_acc[MP_OSC_CH_COUNT];

/* LFSR state for noise channel */
static uint16_t mp_osc_lfsr;

void mp_osc_init(void) {
    memset(mp_osc_params_array, 0, sizeof(mp_osc_params_array));
    memset(mp_osc_phase_acc, 0, sizeof(mp_osc_phase_acc));

    for (uint8_t i = 0; i < MP_OSC_CH_COUNT; i++) {
        mp_osc_params_array[i].mod = MP_OSC_MOD_DEFAULT;
        mp_osc_params_array[i].waveform = MP_WAVE_SQUARE;
    }

    mp_osc_lfsr = 1;
}

/*
 * Generate one sample for a melodic channel.
 * Returns a signed value in range [-vol, +vol].
 * All integer math, no division (uses shifts and multiplies).
 */
static inline int16_t osc_generate_sample(const struct mp_osc_params* p, uint8_t phase_hi) {
    int16_t vol = p->vol;

    switch (p->waveform) {
    case MP_WAVE_TRIANGLE: {
        /*
         * Triangle wave from 8-bit phase:
         *   0..127:   ramp up   -> sample = phase * 2 - 128  (maps to -128..+126)
         *   128..255: ramp down -> sample = (255 - phase) * 2 - 128
         * Then scale by vol/128 to get range [-vol, +vol]
         */
        int16_t tri;
        if (phase_hi < 128) {
            tri = (int16_t)phase_hi * 2 - 128;
        } else {
            tri = (int16_t)(255 - phase_hi) * 2 - 128;
        }
        /* Scale: tri is -128..+126, vol is 0..127 */
        return (int16_t)(tri * vol / 128);
    }

    case MP_WAVE_SAWTOOTH: {
        /*
         * Sawtooth wave: linear ramp from -vol to +vol
         *   sample = phase * 2 - 256, scaled by vol/128
         *   = (phase - 128) * vol / 128
         */
        int16_t saw = (int16_t)phase_hi - 128;
        return (int16_t)(saw * vol / 128);
    }

    case MP_WAVE_PULSE_25:
        /* Fixed 25% duty cycle pulse */
        return (phase_hi < 64) ? vol : -vol;

    case MP_WAVE_SQUARE:
    default:
        /* Square wave with variable duty cycle (mod) */
        return (phase_hi < p->mod) ? vol : -vol;
    }
}

uint16_t mp_osc_mix_sample(void) {
    int16_t mix = MP_OSC_DC_OFFSET;

    /* Process noise channel (last channel) */
    {
        uint16_t lfsr = mp_osc_lfsr;
        uint8_t feedback = ((lfsr >> 15) ^ (lfsr >> 14)) & 1;
        lfsr = (lfsr << 1) | feedback;
        mp_osc_lfsr = lfsr;

        uint8_t vol = mp_osc_params_array[MP_OSC_NOISE_CH].vol;
        if (lfsr & 0x8000) {
            mix += vol;
        } else {
            mix -= vol;
        }
    }

    /* Process melodic channels */
    for (uint8_t i = 0; i < MP_OSC_NOISE_CH; i++) {
        struct mp_osc_params* p = &mp_osc_params_array[i];

        mp_osc_phase_acc[i] += p->phase_increment;
        uint8_t phase_hi = mp_osc_phase_acc[i] >> 8;

        mix += osc_generate_sample(p, phase_hi);
    }

    /* Clamp to 10-bit range */
    if (mix < 0) {
        mix = 0;
    } else if (mix > 1023) {
        mix = 1023;
    }

    return (uint16_t)mix;
}

struct mp_osc_params* mp_osc_get_params(uint8_t ch) {
    if (ch >= MP_OSC_CH_COUNT) {
        return (struct mp_osc_params*)0;
    }
    return &mp_osc_params_array[ch];
}

void mp_osc_set_freq(uint8_t ch, uint16_t phase_inc) {
    if (ch < MP_OSC_CH_COUNT) {
        mp_osc_params_array[ch].phase_increment = phase_inc;
    }
}

void mp_osc_set_vol(uint8_t ch, uint8_t vol) {
    if (ch < MP_OSC_CH_COUNT) {
        if (vol > MP_OSC_MAX_VOLUME) {
            vol = MP_OSC_MAX_VOLUME;
        }
        mp_osc_params_array[ch].vol = vol;
    }
}

void mp_osc_set_mod(uint8_t ch, uint8_t mod) {
    if (ch < MP_OSC_CH_COUNT) {
        mp_osc_params_array[ch].mod = mod;
    }
}

void mp_osc_set_waveform(uint8_t ch, mp_waveform_t waveform) {
    if (ch < MP_OSC_CH_COUNT && waveform < MP_WAVE_COUNT) {
        mp_osc_params_array[ch].waveform = (uint8_t)waveform;
    }
}

void mp_osc_silence(void) {
    for (uint8_t i = 0; i < MP_OSC_CH_COUNT; i++) {
        mp_osc_params_array[i].vol = 0;
        mp_osc_params_array[i].phase_increment = 0;
    }
}
