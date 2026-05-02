/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Unit tests for mp_envelope (ADSR envelope generator)
 */
#include "test_framework.h"
#include "mp_envelope.h"
#include "mp_osc.h"

/* --- Init tests --- */

static void test_env_init_idle(void) {
    mp_osc_init();
    mp_env_init();
    for (uint8_t ch = 0; ch < MP_OSC_CH_COUNT; ch++) {
        TEST_ASSERT_EQUAL(0, mp_env_get_level(ch));
    }
}

/* --- Attack tests --- */

static void test_env_attack_ramps_up(void) {
    mp_osc_init();
    mp_env_init();

    /* Use a preset with measurable attack */
    mp_adsr_params_t p = {.attack = 100, .decay = 0, .sustain = 255, .release = 100};
    mp_env_set_adsr(0, &p);

    mp_env_note_on(0, 100);

    /* After a few ticks, level should be rising */
    for (int i = 0; i < 10; i++) {
        mp_env_tick();
    }
    uint8_t mid_level = mp_env_get_level(0);
    TEST_ASSERT_TRUE(mid_level > 0);
    TEST_ASSERT_TRUE(mid_level < 100);

    /* After full attack, should reach peak */
    for (int i = 0; i < 100; i++) {
        mp_env_tick();
    }
    TEST_ASSERT_EQUAL(100, mp_env_get_level(0));
}

static void test_env_instant_attack(void) {
    mp_osc_init();
    mp_env_init();

    mp_adsr_params_t p = {.attack = 0, .decay = 0, .sustain = 255, .release = 0};
    mp_env_set_adsr(0, &p);

    mp_env_note_on(0, 80);
    mp_env_tick();
    TEST_ASSERT_EQUAL(80, mp_env_get_level(0));
}

/* --- Decay tests --- */

static void test_env_decay_to_sustain(void) {
    mp_osc_init();
    mp_env_init();

    /* sustain = 128 means 50% of peak */
    mp_adsr_params_t p = {.attack = 0, .decay = 100, .sustain = 128, .release = 100};
    mp_env_set_adsr(0, &p);

    mp_env_note_on(0, 100);

    /* Run through decay */
    for (int i = 0; i < 110; i++) {
        mp_env_tick();
    }

    /* Should be at sustain level: 100 * 128 / 255 ≈ 50 */
    uint8_t level = mp_env_get_level(0);
    TEST_ASSERT_IN_RANGE(level, 45, 55);
}

/* --- Release tests --- */

static void test_env_release_ramps_down(void) {
    mp_osc_init();
    mp_env_init();

    mp_adsr_params_t p = {.attack = 0, .decay = 0, .sustain = 255, .release = 200};
    mp_env_set_adsr(0, &p);

    mp_env_note_on(0, 100);
    mp_env_tick(); /* Sustain at 100 */

    mp_env_note_off(0);

    /* After some release ticks, level should be decreasing */
    for (int i = 0; i < 50; i++) {
        mp_env_tick();
    }
    uint8_t mid_level = mp_env_get_level(0);
    TEST_ASSERT_TRUE(mid_level > 0);
    TEST_ASSERT_TRUE(mid_level < 100);

    /* After full release, should be 0 */
    for (int i = 0; i < 200; i++) {
        mp_env_tick();
    }
    TEST_ASSERT_EQUAL(0, mp_env_get_level(0));
}

static void test_env_instant_release(void) {
    mp_osc_init();
    mp_env_init();

    mp_adsr_params_t p = {.attack = 0, .decay = 0, .sustain = 255, .release = 0};
    mp_env_set_adsr(0, &p);

    mp_env_note_on(0, 80);
    mp_env_tick();
    TEST_ASSERT_EQUAL(80, mp_env_get_level(0));

    mp_env_note_off(0);
    mp_env_tick();
    TEST_ASSERT_EQUAL(0, mp_env_get_level(0));
}

/* --- Preset tests --- */

static void test_env_presets_valid(void) {
    for (int i = 0; i < MP_ADSR_PRESET_COUNT; i++) {
        const mp_adsr_params_t* p = mp_env_get_preset_params((mp_adsr_preset_t)i);
        TEST_ASSERT_NOT_NULL(p);
    }
    TEST_ASSERT_NULL(mp_env_get_preset_params(MP_ADSR_PRESET_COUNT));
}

static void test_env_set_preset_works(void) {
    mp_osc_init();
    mp_env_init();

    /* Piano preset: fast attack */
    mp_env_set_preset(0, MP_ADSR_PRESET_PIANO);
    mp_env_note_on(0, 100);

    /* After a few ticks should already be near peak (attack=4 ticks) */
    for (int i = 0; i < 10; i++) {
        mp_env_tick();
    }
    TEST_ASSERT_TRUE(mp_env_get_level(0) > 80);
}

/* --- Volume modulation test --- */

static void test_env_modulates_osc_volume(void) {
    mp_osc_init();
    mp_env_init();

    mp_adsr_params_t p = {.attack = 0, .decay = 0, .sustain = 255, .release = 0};
    mp_env_set_adsr(0, &p);

    /* Before note_on, osc volume should be 0 */
    struct mp_osc_params* osc = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(0, osc->vol);

    /* After note_on + tick, osc volume should match envelope */
    mp_env_note_on(0, 90);
    mp_env_tick();
    TEST_ASSERT_EQUAL(90, osc->vol);

    /* After note_off + tick, osc volume should be 0 */
    mp_env_note_off(0);
    mp_env_tick();
    TEST_ASSERT_EQUAL(0, osc->vol);
}

/* --- Invalid channel tests --- */

static void test_env_invalid_channel(void) {
    mp_env_init();
    /* Should not crash */
    mp_env_note_on(MP_OSC_CH_COUNT, 100);
    mp_env_note_off(MP_OSC_CH_COUNT);
    TEST_ASSERT_EQUAL(0, mp_env_get_level(MP_OSC_CH_COUNT));
}

void test_envelope_run(void) {
    TEST_SUITE_BEGIN("Envelope (ADSR) Tests");

    RUN_TEST(test_env_init_idle);
    RUN_TEST(test_env_attack_ramps_up);
    RUN_TEST(test_env_instant_attack);
    RUN_TEST(test_env_decay_to_sustain);
    RUN_TEST(test_env_release_ramps_down);
    RUN_TEST(test_env_instant_release);
    RUN_TEST(test_env_presets_valid);
    RUN_TEST(test_env_set_preset_works);
    RUN_TEST(test_env_modulates_osc_volume);
    RUN_TEST(test_env_invalid_channel);

    TEST_SUITE_END();
}
