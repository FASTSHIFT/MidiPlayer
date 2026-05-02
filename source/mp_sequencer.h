/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - MIDI Sequencer
 *
 * Event-driven sequencer that reads pre-converted MIDI data
 * and drives the oscillator channels with ADSR envelope support.
 */
#ifndef MP_SEQUENCER_H
#define MP_SEQUENCER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Maximum number of simultaneous tracks */
#ifndef MP_SEQ_MAX_TRACKS
#define MP_SEQ_MAX_TRACKS 4
#endif

/* Note event structure (compact for Flash storage) */
typedef struct {
    uint32_t start_time_ms; /* Absolute start time in milliseconds */
    uint16_t phase_inc;     /* Phase increment (from note table) */
    uint16_t duration_ms;   /* Note duration in milliseconds */
    uint8_t volume;         /* Velocity (0~127) */
    uint8_t channel;        /* Oscillator channel to use (0~3) */
    uint8_t mod;            /* Duty cycle (0~255, 127=50%, 64=25%) */
    uint8_t adsr_preset;    /* ADSR preset index (mp_adsr_preset_t) */
    uint8_t waveform;       /* Waveform type (mp_waveform_t) */
} mp_note_event_t;

/* Track descriptor */
typedef struct {
    const mp_note_event_t* events; /* Pointer to event array (in Flash) */
    uint32_t event_count;          /* Number of events in this track */
} mp_track_t;

/* Score descriptor */
typedef struct {
    const mp_track_t* tracks; /* Array of tracks */
    uint8_t track_count;      /* Number of tracks */
} mp_score_t;

/**
 * @brief  Initialize the sequencer
 */
void mp_seq_init(void);

/**
 * @brief  Start playing a score
 * @param  score: pointer to score descriptor (must remain valid during playback)
 */
void mp_seq_play(const mp_score_t* score);

/**
 * @brief  Stop playback
 */
void mp_seq_stop(void);

/**
 * @brief  Check if playback is active
 * @retval 1 if playing, 0 if stopped
 */
uint8_t mp_seq_is_playing(void);

/**
 * @brief  Advance the sequencer by one tick
 * @param  current_ms: current time in milliseconds
 * @note   Call this periodically (e.g., at 2kHz from the oscillator prescaler,
 *         or from main loop using mp_port_get_tick_ms())
 */
void mp_seq_tick(uint32_t current_ms);

#ifdef __cplusplus
}
#endif

#endif /* MP_SEQUENCER_H */
