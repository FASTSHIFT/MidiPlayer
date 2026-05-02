/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Integration tests for mp_player (public API)
 */
#include "test_framework.h"
#include "mock_port.h"
#include "mp_player.h"
#include "mp_port.h"

/* Use ORGAN preset for instant attack / full sustain */
#define TEST_ADSR 2

/* Test data */
static const mp_note_event_t player_test_events[] = {
    {.start_time_ms = 0,
     .phase_inc = 1072,
     .duration_ms = 50,
     .volume = 100,
     .channel = 0,
     .mod = 127,
     .adsr_preset = TEST_ADSR},
    {.start_time_ms = 100,
     .phase_inc = 1802,
     .duration_ms = 50,
     .volume = 80,
     .channel = 0,
     .mod = 127,
     .adsr_preset = TEST_ADSR},
};

static const mp_track_t player_test_tracks[] = {
    {.events = player_test_events, .event_count = 2},
};

static const mp_score_t player_test_score = {
    .tracks = player_test_tracks,
    .track_count = 1,
};

static void test_player_init(void) {
    mp_init();
    TEST_ASSERT_FALSE(mp_is_playing());
}

static void test_player_play_stop(void) {
    mp_init();
    mp_play(&player_test_score);
    TEST_ASSERT_TRUE(mp_is_playing());
    mp_stop();
    TEST_ASSERT_FALSE(mp_is_playing());
}

static void test_player_audio_tick_returns_valid(void) {
    mp_init();
    /* Without any notes, should return DC offset */
    uint16_t sample = mp_audio_tick();
    TEST_ASSERT_EQUAL(MP_OSC_DC_OFFSET, sample);
}

static void test_player_full_playback(void) {
    mp_init();
    mock_port_reset();

    mp_play(&player_test_score);
    TEST_ASSERT_TRUE(mp_is_playing());

    /* Simulate playback: update sequencer, generate audio samples */
    for (uint32_t ms = 0; ms < 300; ms++) {
        mp_update(ms);
        for (int s = 0; s < 16; s++) {
            uint16_t sample = mp_audio_tick();
            mp_port_audio_write(sample);
        }
    }

    /* Should have auto-stopped after all notes + release */
    TEST_ASSERT_FALSE(mp_is_playing());
    TEST_ASSERT_TRUE(mock_port_get_audio_count() > 0);
}

static void test_player_audio_has_variation(void) {
    mp_init();
    mock_port_reset();

    mp_play(&player_test_score);

    /* Trigger first note and let attack complete */
    for (uint32_t ms = 0; ms < 5; ms++) {
        mp_update(ms);
    }

    /* Generate samples and check for variation */
    int non_dc_count = 0;
    for (int i = 0; i < 100; i++) {
        uint16_t sample = mp_audio_tick();
        if (sample != MP_OSC_DC_OFFSET) {
            non_dc_count++;
        }
    }

    TEST_ASSERT_TRUE(non_dc_count > 0);
}

void test_player_run(void) {
    TEST_SUITE_BEGIN("Player Integration Tests");

    RUN_TEST(test_player_init);
    RUN_TEST(test_player_play_stop);
    RUN_TEST(test_player_audio_tick_returns_valid);
    RUN_TEST(test_player_full_playback);
    RUN_TEST(test_player_audio_has_variation);

    TEST_SUITE_END();
}
