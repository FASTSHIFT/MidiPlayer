/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - MIDI Note to Phase Increment Table
 *
 * Phase increment = frequency * 65536 / 16000
 * Covers MIDI notes 24 (C1) through 108 (C8).
 * Notes below 24 or above 108 return 0 (out of audible/useful range at 16kHz).
 */
#include "mp_note_table.h"

#define NOTE_TABLE_FIRST_MIDI 24 /* C1 */
#define NOTE_TABLE_LAST_MIDI 108 /* C8 */
#define NOTE_TABLE_SIZE (NOTE_TABLE_LAST_MIDI - NOTE_TABLE_FIRST_MIDI + 1)

/*
 * Pre-computed phase increments for MIDI notes 24..108
 * phase_inc = round(midi_freq(note) * 65536 / 16000)
 *
 * midi_freq(n) = 440 * 2^((n-69)/12)
 */
/* clang-format off */
static const uint16_t note_table[NOTE_TABLE_SIZE] = {
    /* C1  */ 134,   142,   150,   159,   169,   179,   190,   201,   213,   225,   239,   253,
    /* C2  */ 268,   284,   301,   319,   338,   358,   379,   401,   425,   451,   477,   506,
    /* C3  */ 536,   568,   601,   637,   675,   715,   758,   803,   851,   901,   955,  1011,
    /* C4  */ 1072,  1135,  1203,  1274,  1350,  1430,  1515,  1606,  1701,  1802,  1909,  2023,
    /* C5  */ 2143,  2271,  2406,  2549,  2700,  2861,  3031,  3211,  3402,  3604,  3819,  4046,
    /* C6  */ 4286,  4541,  4811,  5098,  5401,  5722,  6062,  6422,  6804,  7209,  7638,  8092,
    /* C7  */ 8573,  9083,  9623, 10196, 10801, 11444, 12125, 12845, 13608, 14418, 15276, 16184,
    /* C8  */ 17146,
};
/* clang-format on */

uint16_t mp_note_to_phase_inc(uint8_t note) {
    if (note < NOTE_TABLE_FIRST_MIDI || note > NOTE_TABLE_LAST_MIDI) {
        return 0;
    }
    return note_table[note - NOTE_TABLE_FIRST_MIDI];
}

uint8_t mp_note_table_size(void) {
    return NOTE_TABLE_SIZE;
}
