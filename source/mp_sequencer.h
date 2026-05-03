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
#define MP_SEQ_MAX_TRACKS 8
#endif

/*
 * Packed note event structure — 8 bytes per event (50% smaller than unpacked).
 *
 * Layout (two 32-bit words, total 64 bits):
 *
 *   Word 0 [31:0]:
 *     start_time_ms [19:0]  — 20 bits, max 1048575 ms (~17 min)
 *     duration_ms   [31:20] — 12 bits, max 4095 ms
 *
 *   Word 1 [31:0]:
 *     phase_inc     [14:0]  — 15 bits, max 32767 (covers C1..C8)
 *     volume        [21:15] —  7 bits, 0~127
 *     channel       [24:22] —  3 bits, 0~7
 *     mod_idx       [26:25] —  2 bits, index into duty cycle table
 *     adsr_preset   [29:27] —  3 bits, 0~7
 *     waveform      [31:30] —  2 bits, 0~3
 */
typedef struct {
    uint32_t word0;
    uint32_t word1;
} mp_note_event_t;

/* Duty cycle lookup table indexed by mod_idx (2 bits, 0~3) */
/* clang-format off */
#define MP_MOD_TABLE_SIZE 4
static const uint8_t mp_mod_table[MP_MOD_TABLE_SIZE] = {
    127,  /* 0: 50%   — classic square */
    64,   /* 1: 25%   — bright, thin */
    32,   /* 2: 12.5% — very thin, nasal */
    191,  /* 3: 75%   — hollow */
};
/* clang-format on */

/* --- Accessor macros for packed fields --- */

#define MP_EVT_START_MS(e) ((e)->word0 & 0xFFFFF)
#define MP_EVT_DURATION_MS(e) ((e)->word0 >> 20)
#define MP_EVT_PHASE_INC(e) ((e)->word1 & 0x7FFF)
#define MP_EVT_VOLUME(e) (((e)->word1 >> 15) & 0x7F)
#define MP_EVT_CHANNEL(e) (((e)->word1 >> 22) & 0x07)
#define MP_EVT_MOD_IDX(e) (((e)->word1 >> 25) & 0x03)
#define MP_EVT_ADSR(e) (((e)->word1 >> 27) & 0x07)
#define MP_EVT_WAVEFORM(e) (((e)->word1 >> 30) & 0x03)

/* Convenience: get actual mod value from index */
#define MP_EVT_MOD(e) (mp_mod_table[MP_EVT_MOD_IDX(e)])

/* --- Pack helper (for converter / tests) --- */

#define MP_EVT_PACK_WORD0(start_ms, dur_ms) (((uint32_t)(start_ms)&0xFFFFF) | (((uint32_t)(dur_ms)&0xFFF) << 20))

#define MP_EVT_PACK_WORD1(phase_inc, vol, ch, mod_idx, adsr, wave)                                   \
    (((uint32_t)(phase_inc)&0x7FFF) | (((uint32_t)(vol)&0x7F) << 15) | (((uint32_t)(ch)&0x07) << 22) \
     | (((uint32_t)(mod_idx)&0x03) << 25) | (((uint32_t)(adsr)&0x07) << 27) | (((uint32_t)(wave)&0x03) << 30))

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
 */
void mp_seq_tick(uint32_t current_ms);

/**
 * @brief  Get elapsed playback time in milliseconds
 */
uint32_t mp_seq_get_elapsed_ms(void);

/**
 * @brief  Get total score duration in milliseconds
 */
uint32_t mp_seq_get_total_ms(void);

/**
 * @brief  Get playback progress as percentage (0~100)
 */
uint8_t mp_seq_get_progress_pct(void);

#ifdef __cplusplus
}
#endif

#endif /* MP_SEQUENCER_H */
