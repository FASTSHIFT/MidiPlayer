/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer - MIDI Note to Phase Increment Table
 *
 * Maps MIDI note numbers (0~127) to phase increment values
 * for the oscillator at 16kHz sample rate.
 */
#ifndef MP_NOTE_TABLE_H
#define MP_NOTE_TABLE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief  Convert MIDI note number to phase increment
 * @param  note: MIDI note number (0~127)
 * @retval Phase increment for mp_osc_set_freq(), 0 if note is out of range
 *
 * Formula: phase_inc = freq * 65536 / SAMPLE_RATE
 * Example: A4 (note 69) = 440Hz -> 440 * 65536 / 16000 = 1802
 */
uint16_t mp_note_to_phase_inc(uint8_t note);

/**
 * @brief  Get the number of supported MIDI notes
 * @retval Number of entries in the note table
 */
uint8_t mp_note_table_size(void);

#ifdef __cplusplus
}
#endif

#endif /* MP_NOTE_TABLE_H */
