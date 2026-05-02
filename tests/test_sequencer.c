/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Unit tests for mp_sequencer
 */
#include "test_framework.h"
#include "mock_port.h"
#include "mp_envelope.h"
#include "mp_osc.h"
#include "mp_sequencer.h"

/*
 * Use ORGAN preset (index 2): instant attack, full sustain, fast release.
 * This gives deterministic volume behavior for testing.
 */
#define TEST_MOD 127
#define TEST_ADSR 2 /* MP_ADSR_PRESET_ORGAN */

/* Test data: simple 2-note sequence on channel 0 */
static const mp_note_event_t test_events_ch0[] = {
    {.start_time_ms = 0,
     .phase_inc = 1072,
     .duration_ms = 100,
     .volume = 80,
     .channel = 0,
     .mod = TEST_MOD,
     .adsr_preset = TEST_ADSR,
     .waveform = 0},
    {.start_time_ms = 200,
     .phase_inc = 1802,
     .duration_ms = 100,
     .volume = 60,
     .channel = 0,
     .mod = TEST_MOD,
     .adsr_preset = TEST_ADSR,
     .waveform = 0},
};

static const mp_track_t test_tracks[] = {
    {.events = test_events_ch0, .event_count = 2},
};

static const mp_score_t test_score = {
    .tracks = test_tracks,
    .track_count = 1,
};

/* --- Init tests --- */

static void test_seq_init_not_playing(void) {
    mp_seq_init();
    TEST_ASSERT_FALSE(mp_seq_is_playing());
}

/* --- Play/Stop tests --- */

static void test_seq_play_starts(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_play(&test_score);
    TEST_ASSERT_TRUE(mp_seq_is_playing());
}

static void test_seq_stop(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_play(&test_score);
    mp_seq_stop();
    TEST_ASSERT_FALSE(mp_seq_is_playing());
}

static void test_seq_play_null_score(void) {
    mp_seq_init();
    mp_seq_play(NULL);
    TEST_ASSERT_FALSE(mp_seq_is_playing());
}

/* --- Tick / event processing tests --- */

static void test_seq_first_note_triggers(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_play(&test_score);

    /* First tick triggers note + envelope tick */
    mp_seq_tick(1000);

    struct mp_osc_params* p = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(1072, p->phase_increment);
    /* ORGAN preset: attack=2 ticks, so after 1 tick we're ramping.
       Run a couple more ticks to reach peak. */
    mp_seq_tick(1001);
    mp_seq_tick(1002);
    TEST_ASSERT_EQUAL(80, p->vol);
}

static void test_seq_note_off_after_duration(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_play(&test_score);

    /* Trigger and let attack complete */
    for (uint32_t t = 1000; t < 1005; t++) {
        mp_seq_tick(t);
    }

    struct mp_osc_params* p = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(80, p->vol);

    /* After 100ms, note releases. ORGAN release=100 ticks (50ms).
       Run enough ticks for release to complete. */
    for (uint32_t t = 1100; t < 1200; t++) {
        mp_seq_tick(t);
    }
    TEST_ASSERT_EQUAL(0, p->vol);
}

static void test_seq_second_note_triggers(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_play(&test_score);

    /* Process through first note and its release */
    for (uint32_t t = 1000; t < 1200; t++) {
        mp_seq_tick(t);
    }

    /* At 200ms, second note triggers */
    mp_seq_tick(1200);
    mp_seq_tick(1201);
    mp_seq_tick(1202);

    struct mp_osc_params* p = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(1802, p->phase_increment);
    TEST_ASSERT_EQUAL(60, p->vol);
}

static void test_seq_auto_stop_after_all_notes(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_play(&test_score);

    /* Run through entire score with enough time for all envelopes */
    for (uint32_t t = 1000; t < 1500; t++) {
        mp_seq_tick(t);
    }

    TEST_ASSERT_FALSE(mp_seq_is_playing());
}

/* --- Multi-track test --- */

static const mp_note_event_t test_events_ch1[] = {
    {.start_time_ms = 50,
     .phase_inc = 536,
     .duration_ms = 150,
     .volume = 70,
     .channel = 1,
     .mod = TEST_MOD,
     .adsr_preset = TEST_ADSR,
     .waveform = 0},
};

static const mp_track_t test_multi_tracks[] = {
    {.events = test_events_ch0, .event_count = 2},
    {.events = test_events_ch1, .event_count = 1},
};

static const mp_score_t test_multi_score = {
    .tracks = test_multi_tracks,
    .track_count = 2,
};

static void test_seq_multitrack_simultaneous(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_play(&test_multi_score);

    /* Tick through to let both notes trigger and attack complete */
    for (uint32_t t = 1000; t < 1055; t++) {
        mp_seq_tick(t);
    }

    struct mp_osc_params* p0 = mp_osc_get_params(0);
    struct mp_osc_params* p1 = mp_osc_get_params(1);

    TEST_ASSERT_EQUAL(1072, p0->phase_increment);
    TEST_ASSERT_EQUAL(80, p0->vol);
    TEST_ASSERT_EQUAL(536, p1->phase_increment);
    TEST_ASSERT_EQUAL(70, p1->vol);
}

/* --- Duty cycle test --- */

static const mp_note_event_t test_events_mod[] = {
    {.start_time_ms = 0,
     .phase_inc = 1072,
     .duration_ms = 100,
     .volume = 80,
     .channel = 0,
     .mod = 64,
     .adsr_preset = TEST_ADSR,
     .waveform = 0},
};

static const mp_track_t test_tracks_mod[] = {
    {.events = test_events_mod, .event_count = 1},
};

static const mp_score_t test_score_mod = {
    .tracks = test_tracks_mod,
    .track_count = 1,
};

static void test_seq_duty_cycle_applied(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_play(&test_score_mod);

    mp_seq_tick(1000);

    struct mp_osc_params* p = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(64, p->mod); /* 25% duty cycle */
}

void test_sequencer_run(void) {
    TEST_SUITE_BEGIN("Sequencer Tests");

    RUN_TEST(test_seq_init_not_playing);
    RUN_TEST(test_seq_play_starts);
    RUN_TEST(test_seq_stop);
    RUN_TEST(test_seq_play_null_score);
    RUN_TEST(test_seq_first_note_triggers);
    RUN_TEST(test_seq_note_off_after_duration);
    RUN_TEST(test_seq_second_note_triggers);
    RUN_TEST(test_seq_auto_stop_after_all_notes);
    RUN_TEST(test_seq_multitrack_simultaneous);
    RUN_TEST(test_seq_duty_cycle_applied);

    TEST_SUITE_END();
}
