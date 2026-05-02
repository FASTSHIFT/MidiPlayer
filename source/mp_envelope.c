/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - ADSR Envelope Generator Implementation
 *
 * Linear ADSR envelope running at 2kHz tick rate.
 * Modulates oscillator volume per channel.
 */
#include "mp_envelope.h"
#include "mp_osc.h"
#include <string.h>

/* Per-channel ADSR parameters and state */
static mp_adsr_params_t env_params[MP_OSC_CH_COUNT];
static mp_env_state_t env_state[MP_OSC_CH_COUNT];

/* Preset ADSR profiles (times in ticks at 2kHz, 1 tick = 0.5ms)
 *
 * attack=20  -> 10ms
 * attack=100 -> 50ms
 * decay=200  -> 100ms
 * release=400 -> 200ms
 */
/* clang-format off */
static const mp_adsr_params_t adsr_presets[MP_ADSR_PRESET_COUNT] = {
    /* DEFAULT:  moderate attack, some decay, good sustain */
    [MP_ADSR_PRESET_DEFAULT] = { .attack = 10,  .decay = 200,  .sustain = 200, .release = 200 },
    /* PIANO:    fast attack, long decay, low sustain (percussive) */
    [MP_ADSR_PRESET_PIANO]   = { .attack = 4,   .decay = 800,  .sustain = 80,  .release = 400 },
    /* ORGAN:    instant attack, no decay, full sustain */
    [MP_ADSR_PRESET_ORGAN]   = { .attack = 2,   .decay = 0,    .sustain = 255, .release = 100 },
    /* STRINGS:  slow attack, no decay, full sustain, slow release */
    [MP_ADSR_PRESET_STRINGS] = { .attack = 200, .decay = 0,    .sustain = 255, .release = 600 },
    /* BASS:     fast attack, medium decay, medium sustain */
    [MP_ADSR_PRESET_BASS]    = { .attack = 6,   .decay = 400,  .sustain = 160, .release = 200 },
    /* LEAD:     fast attack, short decay, high sustain */
    [MP_ADSR_PRESET_LEAD]    = { .attack = 8,   .decay = 100,  .sustain = 220, .release = 150 },
    /* PAD:      slow attack, no decay, full sustain, very slow release */
    [MP_ADSR_PRESET_PAD]     = { .attack = 400, .decay = 0,    .sustain = 255, .release = 1000 },
};
/* clang-format on */

void mp_env_init(void) {
    memset(env_state, 0, sizeof(env_state));
    /* Default all channels to DEFAULT preset */
    for (uint8_t i = 0; i < MP_OSC_CH_COUNT; i++) {
        env_params[i] = adsr_presets[MP_ADSR_PRESET_DEFAULT];
    }
}

void mp_env_set_adsr(uint8_t ch, const mp_adsr_params_t* params) {
    if (ch < MP_OSC_CH_COUNT && params) {
        env_params[ch] = *params;
    }
}

void mp_env_set_preset(uint8_t ch, mp_adsr_preset_t preset) {
    if (ch < MP_OSC_CH_COUNT && preset < MP_ADSR_PRESET_COUNT) {
        env_params[ch] = adsr_presets[preset];
    }
}

void mp_env_note_on(uint8_t ch, uint8_t velocity) {
    if (ch >= MP_OSC_CH_COUNT) {
        return;
    }

    mp_env_state_t* s = &env_state[ch];
    s->peak_vol = velocity;
    /* Compute sustain volume: sustain is 0~255 fraction of peak */
    s->sustain_vol = (uint8_t)((uint16_t)velocity * env_params[ch].sustain / 255);

    if (env_params[ch].attack > 0) {
        s->stage = MP_ENV_ATTACK;
        s->counter = env_params[ch].attack;
        s->level = 0;
    } else {
        /* Instant attack */
        s->level = velocity;
        if (env_params[ch].decay > 0) {
            s->stage = MP_ENV_DECAY;
            s->counter = env_params[ch].decay;
        } else {
            s->stage = MP_ENV_SUSTAIN;
            s->level = s->sustain_vol;
        }
    }
}

void mp_env_note_off(uint8_t ch) {
    if (ch >= MP_OSC_CH_COUNT) {
        return;
    }

    mp_env_state_t* s = &env_state[ch];
    if (s->stage == MP_ENV_IDLE) {
        return;
    }

    if (env_params[ch].release > 0) {
        s->stage = MP_ENV_RELEASE;
        s->counter = env_params[ch].release;
        /* level stays at current value, will ramp down to 0 */
    } else {
        /* Instant release */
        s->stage = MP_ENV_IDLE;
        s->level = 0;
    }
}

void mp_env_tick(void) {
    for (uint8_t ch = 0; ch < MP_OSC_CH_COUNT; ch++) {
        mp_env_state_t* s = &env_state[ch];
        const mp_adsr_params_t* p = &env_params[ch];

        switch (s->stage) {
        case MP_ENV_ATTACK:
            if (s->counter > 0) {
                /* Linear ramp from 0 to peak_vol */
                uint16_t elapsed = p->attack - s->counter;
                s->level = (uint8_t)((uint16_t)s->peak_vol * elapsed / p->attack);
                s->counter--;
            }
            if (s->counter == 0) {
                s->level = s->peak_vol;
                if (p->decay > 0) {
                    s->stage = MP_ENV_DECAY;
                    s->counter = p->decay;
                } else {
                    s->stage = MP_ENV_SUSTAIN;
                    s->level = s->sustain_vol;
                }
            }
            break;

        case MP_ENV_DECAY:
            if (s->counter > 0) {
                /* Linear ramp from peak_vol to sustain_vol */
                uint16_t elapsed = p->decay - s->counter;
                int16_t delta = (int16_t)s->peak_vol - s->sustain_vol;
                s->level = s->peak_vol - (uint8_t)((uint16_t)delta * elapsed / p->decay);
                s->counter--;
            }
            if (s->counter == 0) {
                s->level = s->sustain_vol;
                s->stage = MP_ENV_SUSTAIN;
            }
            break;

        case MP_ENV_SUSTAIN:
            /* Hold at sustain level until note_off */
            s->level = s->sustain_vol;
            break;

        case MP_ENV_RELEASE: {
            if (s->counter > 0) {
                /* Linear ramp from current level at release start to 0 */
                /* We use sustain_vol as the starting point of release */
                uint16_t elapsed = p->release - s->counter;
                uint8_t start_level = s->sustain_vol;
                if (elapsed < p->release) {
                    s->level = start_level - (uint8_t)((uint16_t)start_level * elapsed / p->release);
                } else {
                    s->level = 0;
                }
                s->counter--;
            }
            if (s->counter == 0) {
                s->level = 0;
                s->stage = MP_ENV_IDLE;
            }
            break;
        }

        case MP_ENV_IDLE:
        default:
            s->level = 0;
            break;
        }

        /* Apply envelope level to oscillator volume */
        /* level is 0~127 (same range as osc volume) */
        mp_osc_set_vol(ch, s->level);
    }
}

uint8_t mp_env_get_level(uint8_t ch) {
    if (ch >= MP_OSC_CH_COUNT) {
        return 0;
    }
    return env_state[ch].level;
}

const mp_adsr_params_t* mp_env_get_preset_params(mp_adsr_preset_t preset) {
    if (preset >= MP_ADSR_PRESET_COUNT) {
        return (const mp_adsr_params_t*)0;
    }
    return &adsr_presets[preset];
}
