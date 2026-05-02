/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - MIDI Sequencer Implementation
 *
 * Event-driven sequencer with ADSR envelope and duty cycle support.
 */
#include "mp_sequencer.h"
#include "mp_envelope.h"
#include "mp_osc.h"

/* Per-track playback state */
typedef struct {
    const mp_note_event_t* events;
    uint32_t event_count;
    uint32_t next_event_idx;  /* Index of next event to process */
    uint32_t active_off_time; /* When the current note should release (0 = no active note) */
    uint8_t channel;          /* Oscillator channel assigned to this track */
} mp_track_state_t;

/* Sequencer state */
static struct {
    mp_track_state_t tracks[MP_SEQ_MAX_TRACKS];
    uint8_t track_count;
    uint8_t playing;
    uint32_t start_ms; /* Timestamp when playback started */
} seq_state;

void mp_seq_init(void) {
    seq_state.track_count = 0;
    seq_state.playing = 0;
    seq_state.start_ms = 0;
}

void mp_seq_play(const mp_score_t* score) {
    if (!score || score->track_count == 0) {
        return;
    }

    mp_osc_silence();
    mp_env_init();
    mp_seq_init();

    uint8_t count = score->track_count;
    if (count > MP_SEQ_MAX_TRACKS) {
        count = MP_SEQ_MAX_TRACKS;
    }

    for (uint8_t i = 0; i < count; i++) {
        seq_state.tracks[i].events = score->tracks[i].events;
        seq_state.tracks[i].event_count = score->tracks[i].event_count;
        seq_state.tracks[i].next_event_idx = 0;
        seq_state.tracks[i].active_off_time = 0;
        seq_state.tracks[i].channel = i;
    }

    seq_state.track_count = count;
    seq_state.playing = 1;
    seq_state.start_ms = 0;
}

void mp_seq_stop(void) {
    seq_state.playing = 0;
    mp_osc_silence();
}

uint8_t mp_seq_is_playing(void) {
    return seq_state.playing;
}

void mp_seq_tick(uint32_t current_ms) {
    if (!seq_state.playing) {
        return;
    }

    /* Set start time on first tick */
    if (seq_state.start_ms == 0) {
        seq_state.start_ms = current_ms;
    }

    uint32_t elapsed = current_ms - seq_state.start_ms;
    uint8_t all_done = 1;

    for (uint8_t t = 0; t < seq_state.track_count; t++) {
        mp_track_state_t* ts = &seq_state.tracks[t];

        /* Check if current note should enter release phase */
        if (ts->active_off_time > 0 && elapsed >= ts->active_off_time) {
            mp_env_note_off(ts->channel);
            mp_osc_set_freq(ts->channel, 0);
            ts->active_off_time = 0;
        }

        /* Process new events that are due */
        while (ts->next_event_idx < ts->event_count) {
            const mp_note_event_t* ev = &ts->events[ts->next_event_idx];

            if (ev->start_time_ms > elapsed) {
                break;
            }

            /* Determine channel */
            uint8_t ch = ev->channel < MP_OSC_CH_COUNT ? ev->channel : ts->channel;

            /* Set duty cycle for this note */
            uint8_t mod = ev->mod > 0 ? ev->mod : MP_OSC_MOD_DEFAULT;
            mp_osc_set_mod(ch, mod);

            /* Set ADSR preset for this channel */
            mp_env_set_preset(ch, (mp_adsr_preset_t)ev->adsr_preset);

            /* Set frequency */
            mp_osc_set_freq(ch, ev->phase_inc);

            /* Trigger envelope (handles volume ramping) */
            mp_env_note_on(ch, ev->volume);

            /* Schedule note-off (release) */
            ts->active_off_time = ev->start_time_ms + ev->duration_ms;

            ts->next_event_idx++;
        }

        /* Track is not done if there are remaining events or an active note */
        if (ts->next_event_idx < ts->event_count || ts->active_off_time > 0) {
            all_done = 0;
        }
    }

    /* Process envelope tick for all channels */
    mp_env_tick();

    if (all_done) {
        /* Check if any envelope is still releasing */
        uint8_t env_active = 0;
        for (uint8_t ch = 0; ch < MP_OSC_CH_COUNT; ch++) {
            if (mp_env_get_level(ch) > 0) {
                env_active = 1;
                break;
            }
        }
        if (!env_active) {
            mp_seq_stop();
        }
    }
}
