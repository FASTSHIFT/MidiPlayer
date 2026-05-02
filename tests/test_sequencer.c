/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Unit tests for mp_sequencer
 */
#include "test_framework.h"
#include "mock_port.h"
#include "mp_osc.h"
#include "mp_sequencer.h"

/* Test data: simple 2-note sequence on channel 0 */
static const mp_note_event_t test_events_ch0[] = {
    {.start_time_ms = 0, .phase_inc = 1072, .duration_ms = 100, .volume = 80, .channel = 0},
    {.start_time_ms = 200, .phase_inc = 1802, .duration_ms = 100, .volume = 60, .channel = 0},
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
    mp_seq_init();
    mp_seq_play(&test_score);
    TEST_ASSERT_TRUE(mp_seq_is_playing());
}

static void test_seq_stop(void) {
    mp_osc_init();
    mp_seq_init();
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
    mp_seq_init();
    mp_seq_play(&test_score);

    /* First tick at time 0 should trigger first note */
    mock_port_set_tick(1000); /* Arbitrary start time */
    mp_seq_tick(1000);

    struct mp_osc_params* p = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(1072, p->phase_increment);
    TEST_ASSERT_EQUAL(80, p->vol);
}

static void test_seq_note_off_after_duration(void) {
    mp_osc_init();
    mp_seq_init();
    mp_seq_play(&test_score);

    /* Trigger first note */
    mp_seq_tick(1000);

    struct mp_osc_params* p = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(80, p->vol);

    /* After 100ms, note should stop */
    mp_seq_tick(1100);
    TEST_ASSERT_EQUAL(0, p->vol);
}

static void test_seq_second_note_triggers(void) {
    mp_osc_init();
    mp_seq_init();
    mp_seq_play(&test_score);

    /* Process through first note */
    mp_seq_tick(1000);
    mp_seq_tick(1100); /* First note off */

    /* At 200ms, second note should trigger */
    mp_seq_tick(1200);

    struct mp_osc_params* p = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(1802, p->phase_increment);
    TEST_ASSERT_EQUAL(60, p->vol);
}

static void test_seq_auto_stop_after_all_notes(void) {
    mp_osc_init();
    mp_seq_init();
    mp_seq_play(&test_score);

    /* Process all notes */
    mp_seq_tick(1000); /* Note 1 on */
    mp_seq_tick(1100); /* Note 1 off */
    mp_seq_tick(1200); /* Note 2 on */
    mp_seq_tick(1300); /* Note 2 off */

    /* Should auto-stop */
    TEST_ASSERT_FALSE(mp_seq_is_playing());
}

/* --- Multi-track test --- */

static const mp_note_event_t test_events_ch1[] = {
    {.start_time_ms = 50, .phase_inc = 536, .duration_ms = 150, .volume = 70, .channel = 1},
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
    mp_seq_init();
    mp_seq_play(&test_multi_score);

    /* At time 50ms, both tracks should have notes active */
    mp_seq_tick(1000); /* t=0: ch0 note on */
    mp_seq_tick(1050); /* t=50: ch1 note on */

    struct mp_osc_params* p0 = mp_osc_get_params(0);
    struct mp_osc_params* p1 = mp_osc_get_params(1);

    TEST_ASSERT_EQUAL(1072, p0->phase_increment);
    TEST_ASSERT_EQUAL(80, p0->vol);
    TEST_ASSERT_EQUAL(536, p1->phase_increment);
    TEST_ASSERT_EQUAL(70, p1->vol);
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

    TEST_SUITE_END();
}
