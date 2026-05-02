/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Demo MIDI data - Simple test melody
 * Two channels playing a short sequence for hardware verification.
 */
#ifndef MIDI_DATA_H
#define MIDI_DATA_H

#include "mp_sequencer.h"
#include "mp_note_table.h"

/* Channel 0: Melody - C4 E4 G4 C5 */
static const mp_note_event_t demo_melody[] = {
    {.start_time_ms = 0, .phase_inc = 1072, .duration_ms = 400, .volume = 100, .channel = 0},    /* C4 */
    {.start_time_ms = 500, .phase_inc = 1350, .duration_ms = 400, .volume = 100, .channel = 0},  /* E4 */
    {.start_time_ms = 1000, .phase_inc = 1606, .duration_ms = 400, .volume = 100, .channel = 0}, /* G4 */
    {.start_time_ms = 1500, .phase_inc = 2143, .duration_ms = 800, .volume = 100, .channel = 0}, /* C5 */
};

/* Channel 1: Bass - C3 C3 G2 C3 */
static const mp_note_event_t demo_bass[] = {
    {.start_time_ms = 0, .phase_inc = 536, .duration_ms = 400, .volume = 80, .channel = 1},    /* C3 */
    {.start_time_ms = 500, .phase_inc = 536, .duration_ms = 400, .volume = 80, .channel = 1},  /* C3 */
    {.start_time_ms = 1000, .phase_inc = 401, .duration_ms = 400, .volume = 80, .channel = 1}, /* G2 */
    {.start_time_ms = 1500, .phase_inc = 536, .duration_ms = 800, .volume = 80, .channel = 1}, /* C3 */
};

static const mp_track_t demo_tracks[] = {
    {.events = demo_melody, .event_count = sizeof(demo_melody) / sizeof(demo_melody[0])},
    {.events = demo_bass, .event_count = sizeof(demo_bass) / sizeof(demo_bass[0])},
};

static const mp_score_t demo_score = {
    .tracks = demo_tracks,
    .track_count = 2,
};

#endif /* MIDI_DATA_H */
