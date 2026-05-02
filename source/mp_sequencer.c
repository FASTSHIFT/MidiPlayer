/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - MIDI Sequencer Implementation
 *
 * Event-driven sequencer with ADSR envelope, duty cycle, and waveform support.
 * Uses packed 8-byte note events for compact Flash storage.
 */
#include "mp_sequencer.h"
#include "mp_envelope.h"
#include "mp_osc.h"

/* Per-track playback state */
typedef struct {
    const mp_note_event_t* events;
    uint32_t event_count;
    uint32_t next_event_idx;
    uint32_t active_off_time; /* 0 = no active note */
    uint8_t channel;
} mp_track_state_t;

/* Sequencer state */
static struct {
    mp_track_state_t tracks[MP_SEQ_MAX_TRACKS];
    uint8_t track_count;
    uint8_t playing;
    uint32_t start_ms;
    uint32_t total_duration_ms; /* Total score duration */
    uint32_t last_elapsed_ms;   /* Last computed elapsed time */
} seq_state;

void mp_seq_init(void) {
    seq_state.track_count = 0;
    seq_state.playing = 0;
    seq_state.start_ms = 0;
    seq_state.total_duration_ms = 0;
    seq_state.last_elapsed_ms = 0;
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

    /* Compute total score duration from all tracks */
    uint32_t max_end = 0;
    for (uint8_t i = 0; i < count; i++) {
        const mp_track_t* trk = &score->tracks[i];
        if (trk->event_count > 0) {
            const mp_note_event_t* last = &trk->events[trk->event_count - 1];
            uint32_t end = MP_EVT_START_MS(last) + MP_EVT_DURATION_MS(last);
            if (end > max_end) {
                max_end = end;
            }
        }
    }
    seq_state.total_duration_ms = max_end;
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

    if (seq_state.start_ms == 0) {
        seq_state.start_ms = current_ms;
    }

    uint32_t elapsed = current_ms - seq_state.start_ms;
    seq_state.last_elapsed_ms = elapsed;
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
            uint32_t ev_start = MP_EVT_START_MS(ev);

            if (ev_start > elapsed) {
                break;
            }

            /* Unpack event fields */
            uint8_t ch = MP_EVT_CHANNEL(ev);
            if (ch >= MP_OSC_CH_COUNT) {
                ch = ts->channel;
            }

            mp_osc_set_mod(ch, MP_EVT_MOD(ev));
            mp_osc_set_waveform(ch, (mp_waveform_t)MP_EVT_WAVEFORM(ev));
            mp_env_set_preset(ch, (mp_adsr_preset_t)MP_EVT_ADSR(ev));
            mp_osc_set_freq(ch, MP_EVT_PHASE_INC(ev));
            mp_env_note_on(ch, MP_EVT_VOLUME(ev));

            ts->active_off_time = ev_start + MP_EVT_DURATION_MS(ev);
            ts->next_event_idx++;
        }

        if (ts->next_event_idx < ts->event_count || ts->active_off_time > 0) {
            all_done = 0;
        }
    }

    /* Process envelope tick for all channels */
    mp_env_tick();

    if (all_done) {
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

uint32_t mp_seq_get_elapsed_ms(void) {
    return seq_state.last_elapsed_ms;
}

uint32_t mp_seq_get_total_ms(void) {
    return seq_state.total_duration_ms;
}

uint8_t mp_seq_get_progress_pct(void) {
    if (seq_state.total_duration_ms == 0) {
        return 0;
    }
    uint32_t pct = seq_state.last_elapsed_ms * 100 / seq_state.total_duration_ms;
    return pct > 100 ? 100 : (uint8_t)pct;
}
