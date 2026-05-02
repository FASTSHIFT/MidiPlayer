/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - Public API Implementation
 */
#include "mp_player.h"
#include "mp_envelope.h"

void mp_init(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_init();
}

void mp_play(const mp_score_t* score) {
    mp_seq_play(score);
}

void mp_stop(void) {
    mp_seq_stop();
}

uint8_t mp_is_playing(void) {
    return mp_seq_is_playing();
}

uint16_t mp_audio_tick(void) {
    return mp_osc_mix_sample();
}

void mp_update(uint32_t current_ms) {
    mp_seq_tick(current_ms);
}
