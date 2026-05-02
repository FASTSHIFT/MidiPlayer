/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - Oscillator / Mixer Implementation
 *
 * Ported from ATMLib2 osc.c (AVR assembly) to portable C.
 * Core algorithm: phase accumulator + threshold comparison for square waves,
 * 16-bit LFSR for noise channel, integer addition mixing with DC offset.
 */
#include "mp_osc.h"
#include <string.h>

/* Channel state */
struct mp_osc_params mp_osc_params_array[MP_OSC_CH_COUNT];
static uint16_t mp_osc_phase_acc[MP_OSC_CH_COUNT];

/* LFSR state for noise channel (stored in phase_acc of noise channel) */
/* We use a separate variable for clarity */
static uint16_t mp_osc_lfsr;

void mp_osc_init(void) {
    memset(mp_osc_params_array, 0, sizeof(mp_osc_params_array));
    memset(mp_osc_phase_acc, 0, sizeof(mp_osc_phase_acc));

    /* Set default 50% duty cycle for all channels */
    for (uint8_t i = 0; i < MP_OSC_CH_COUNT; i++) {
        mp_osc_params_array[i].mod = MP_OSC_MOD_DEFAULT;
    }

    /* Seed LFSR (must be non-zero) */
    mp_osc_lfsr = 1;
}

uint16_t mp_osc_mix_sample(void) {
    int16_t mix = MP_OSC_DC_OFFSET;

    /* Process noise channel (last channel) */
    {
        /* 16-bit LFSR: shift left, XOR feedback from bits 15 and 14 */
        uint16_t lfsr = mp_osc_lfsr;
        uint8_t feedback = ((lfsr >> 15) ^ (lfsr >> 14)) & 1;
        lfsr = (lfsr << 1) | feedback;
        mp_osc_lfsr = lfsr;

        /* Use MSB to determine sign */
        uint8_t vol = mp_osc_params_array[MP_OSC_NOISE_CH].vol;
        if (lfsr & 0x8000) {
            mix += vol;
        } else {
            mix -= vol;
        }
    }

    /* Process square wave channels (all except last) */
    for (uint8_t i = 0; i < MP_OSC_NOISE_CH; i++) {
        struct mp_osc_params* p = &mp_osc_params_array[i];

        /* Advance phase accumulator */
        mp_osc_phase_acc[i] += p->phase_increment;

        /* Get high byte of phase accumulator */
        uint8_t phase_hi = mp_osc_phase_acc[i] >> 8;

        /* Compare with modulation threshold to generate square wave */
        if (phase_hi >= p->mod) {
            mix -= p->vol;
        } else {
            mix += p->vol;
        }
    }

    /* Clamp to 10-bit range (should not be needed with proper volume limits,
       but safety first) */
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

void mp_osc_silence(void) {
    for (uint8_t i = 0; i < MP_OSC_CH_COUNT; i++) {
        mp_osc_params_array[i].vol = 0;
        mp_osc_params_array[i].phase_increment = 0;
    }
}
