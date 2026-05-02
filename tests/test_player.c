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

/* ORGAN preset, square wave */
#define TEST_ADSR 2

static const mp_note_event_t player_test_events[] = {
    {MP_EVT_PACK_WORD0(0, 50), MP_EVT_PACK_WORD1(1072, 100, 0, 0, TEST_ADSR, 0)},
    {MP_EVT_PACK_WORD0(100, 50), MP_EVT_PACK_WORD1(1802, 80, 0, 0, TEST_ADSR, 0)},
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
    uint16_t sample = mp_audio_tick();
    TEST_ASSERT_EQUAL(MP_OSC_DC_OFFSET, sample);
}

static void test_player_full_playback(void) {
    mp_init();
    mock_port_reset();

    mp_play(&player_test_score);
    TEST_ASSERT_TRUE(mp_is_playing());

    for (uint32_t ms = 0; ms < 300; ms++) {
        mp_update(ms);
        for (int s = 0; s < 16; s++) {
            uint16_t sample = mp_audio_tick();
            mp_port_audio_write(sample);
        }
    }

    TEST_ASSERT_FALSE(mp_is_playing());
    TEST_ASSERT_TRUE(mock_port_get_audio_count() > 0);
}

static void test_player_audio_has_variation(void) {
    mp_init();
    mock_port_reset();

    mp_play(&player_test_score);

    for (uint32_t ms = 0; ms < 5; ms++) {
        mp_update(ms);
    }

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
