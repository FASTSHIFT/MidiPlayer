/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Unit tests for mp_sequencer (packed event format)
 */
#include "test_framework.h"
#include "mp_envelope.h"
#include "mp_osc.h"
#include "mp_sequencer.h"

/*
 * Use ORGAN preset (index 2): instant attack, full sustain, fast release.
 * mod_idx=0 (50% duty), waveform=0 (square)
 */
#define TEST_ADSR 2
#define TEST_MOD_IDX 0
#define TEST_WAVE 0

/* Test data: simple 2-note sequence on channel 0 */
/* Note 1: start=0ms, dur=100ms, phase_inc=1072, vol=80, ch=0 */
/* Note 2: start=200ms, dur=100ms, phase_inc=1802, vol=60, ch=0 */
static const mp_note_event_t test_events_ch0[] = {
    {MP_EVT_PACK_WORD0(0, 100), MP_EVT_PACK_WORD1(1072, 80, 0, TEST_MOD_IDX, TEST_ADSR, TEST_WAVE)},
    {MP_EVT_PACK_WORD0(200, 100), MP_EVT_PACK_WORD1(1802, 60, 0, TEST_MOD_IDX, TEST_ADSR, TEST_WAVE)},
};

static const mp_track_t test_tracks[] = {
    {.events = test_events_ch0, .event_count = 2},
};

static const mp_score_t test_score = {
    .tracks = test_tracks,
    .track_count = 1,
};

/* --- Packing tests --- */

static void test_evt_pack_unpack(void) {
    mp_note_event_t ev = {
        MP_EVT_PACK_WORD0(12345, 500),
        MP_EVT_PACK_WORD1(1072, 100, 5, 1, 3, 2),
    };
    TEST_ASSERT_EQUAL(12345, MP_EVT_START_MS(&ev));
    TEST_ASSERT_EQUAL(500, MP_EVT_DURATION_MS(&ev));
    TEST_ASSERT_EQUAL(1072, MP_EVT_PHASE_INC(&ev));
    TEST_ASSERT_EQUAL(100, MP_EVT_VOLUME(&ev));
    TEST_ASSERT_EQUAL(5, MP_EVT_CHANNEL(&ev));
    TEST_ASSERT_EQUAL(1, MP_EVT_MOD_IDX(&ev));
    TEST_ASSERT_EQUAL(64, MP_EVT_MOD(&ev)); /* idx 1 -> 64 (25%) */
    TEST_ASSERT_EQUAL(3, MP_EVT_ADSR(&ev));
    TEST_ASSERT_EQUAL(2, MP_EVT_WAVEFORM(&ev));
}

static void test_evt_pack_max_values(void) {
    /* Max values for each field */
    mp_note_event_t ev = {
        MP_EVT_PACK_WORD0(0xFFFFF, 0xFFF),
        MP_EVT_PACK_WORD1(0x7FFF, 127, 7, 3, 7, 3),
    };
    TEST_ASSERT_EQUAL(0xFFFFF, MP_EVT_START_MS(&ev));
    TEST_ASSERT_EQUAL(0xFFF, MP_EVT_DURATION_MS(&ev));
    TEST_ASSERT_EQUAL(0x7FFF, MP_EVT_PHASE_INC(&ev));
    TEST_ASSERT_EQUAL(127, MP_EVT_VOLUME(&ev));
    TEST_ASSERT_EQUAL(7, MP_EVT_CHANNEL(&ev));
    TEST_ASSERT_EQUAL(3, MP_EVT_MOD_IDX(&ev));
    TEST_ASSERT_EQUAL(7, MP_EVT_ADSR(&ev));
    TEST_ASSERT_EQUAL(3, MP_EVT_WAVEFORM(&ev));
}

static void test_evt_struct_size(void) {
    TEST_ASSERT_EQUAL(8, sizeof(mp_note_event_t));
}

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

    mp_seq_tick(1000);

    struct mp_osc_params* p = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(1072, p->phase_increment);
    /* ORGAN: attack=2 ticks, run a few more to reach peak */
    mp_seq_tick(1001);
    mp_seq_tick(1002);
    TEST_ASSERT_EQUAL(80, p->vol);
}

static void test_seq_note_off_after_duration(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_play(&test_score);

    for (uint32_t t = 1000; t < 1005; t++) {
        mp_seq_tick(t);
    }

    struct mp_osc_params* p = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(80, p->vol);

    /* After 100ms + release (100 ticks = 50ms) */
    for (uint32_t t = 1100; t < 1200; t++) {
        mp_seq_tick(t);
    }
    TEST_ASSERT_EQUAL(0, p->vol);
}

static void test_seq_second_note_triggers(void) {
    mp_osc_init();
    mp_env_init();
    mp_seq_play(&test_score);

    for (uint32_t t = 1000; t < 1200; t++) {
        mp_seq_tick(t);
    }

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

    for (uint32_t t = 1000; t < 1500; t++) {
        mp_seq_tick(t);
    }

    TEST_ASSERT_FALSE(mp_seq_is_playing());
}

/* --- Multi-track test --- */

static const mp_note_event_t test_events_ch1[] = {
    {MP_EVT_PACK_WORD0(50, 150), MP_EVT_PACK_WORD1(536, 70, 1, TEST_MOD_IDX, TEST_ADSR, TEST_WAVE)},
};

/* Test event on channel 5 (beyond old 4-channel limit) */
static const mp_note_event_t test_events_ch5[] = {
    {MP_EVT_PACK_WORD0(0, 100), MP_EVT_PACK_WORD1(1072, 90, 5, TEST_MOD_IDX, TEST_ADSR, TEST_WAVE)},
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

/* Test that channels 4~6 work (expanded from old 3 melodic limit) */
static void test_seq_expanded_channels(void) {
    static const mp_track_t tracks_ch5[] = {
        {.events = test_events_ch5, .event_count = 1},
    };
    static const mp_score_t score_ch5 = {
        .tracks = tracks_ch5,
        .track_count = 1,
    };

    mp_osc_init();
    mp_env_init();
    mp_seq_play(&score_ch5);

    mp_seq_tick(1000);
    mp_seq_tick(1001);
    mp_seq_tick(1002);

    struct mp_osc_params* p5 = mp_osc_get_params(5);
    TEST_ASSERT_EQUAL(1072, p5->phase_increment);
    TEST_ASSERT_EQUAL(90, p5->vol);
}

/* --- Duty cycle test --- */

static const mp_note_event_t test_events_mod[] = {
    {MP_EVT_PACK_WORD0(0, 100), MP_EVT_PACK_WORD1(1072, 80, 0, 1, TEST_ADSR, TEST_WAVE)}, /* mod_idx=1 -> 64 (25%) */
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

    RUN_TEST(test_evt_pack_unpack);
    RUN_TEST(test_evt_pack_max_values);
    RUN_TEST(test_evt_struct_size);
    RUN_TEST(test_seq_init_not_playing);
    RUN_TEST(test_seq_play_starts);
    RUN_TEST(test_seq_stop);
    RUN_TEST(test_seq_play_null_score);
    RUN_TEST(test_seq_first_note_triggers);
    RUN_TEST(test_seq_note_off_after_duration);
    RUN_TEST(test_seq_second_note_triggers);
    RUN_TEST(test_seq_auto_stop_after_all_notes);
    RUN_TEST(test_seq_multitrack_simultaneous);
    RUN_TEST(test_seq_expanded_channels);
    RUN_TEST(test_seq_duty_cycle_applied);

    TEST_SUITE_END();
}
