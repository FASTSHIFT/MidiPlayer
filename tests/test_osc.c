/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Unit tests for mp_osc (oscillator / mixer)
 */
#include "test_framework.h"
#include "mp_osc.h"

/* --- Init tests --- */

static void test_osc_init_silence(void) {
    mp_osc_init();
    /* After init, all volumes should be 0, output should be DC offset */
    uint16_t sample = mp_osc_mix_sample();
    /* With all volumes at 0, output should be exactly DC offset (512) */
    TEST_ASSERT_EQUAL(MP_OSC_DC_OFFSET, sample);
}

static void test_osc_init_default_mod(void) {
    mp_osc_init();
    /* All channels should have 50% duty cycle (mod = 0x7F) */
    for (uint8_t i = 0; i < MP_OSC_CH_COUNT; i++) {
        struct mp_osc_params* p = mp_osc_get_params(i);
        TEST_ASSERT_NOT_NULL(p);
        TEST_ASSERT_EQUAL(MP_OSC_MOD_DEFAULT, p->mod);
        TEST_ASSERT_EQUAL(0, p->vol);
        TEST_ASSERT_EQUAL(0, p->phase_increment);
    }
}

/* --- Single channel tests --- */

static void test_osc_single_channel_output_range(void) {
    mp_osc_init();
    /* Set channel 0 to max volume with a frequency */
    mp_osc_set_vol(0, MP_OSC_MAX_VOLUME);
    mp_osc_set_freq(0, 1000); /* Some frequency */

    /* Generate many samples and check they're in valid range */
    uint16_t min_val = 1023;
    uint16_t max_val = 0;
    for (int i = 0; i < 1000; i++) {
        uint16_t s = mp_osc_mix_sample();
        if (s < min_val)
            min_val = s;
        if (s > max_val)
            max_val = s;
    }

    /* With one channel at max volume (127):
       min = 512 - 127 = 385, max = 512 + 127 = 639 */
    TEST_ASSERT_IN_RANGE(min_val, 0, 1023);
    TEST_ASSERT_IN_RANGE(max_val, 0, 1023);
    /* Should have both positive and negative excursions */
    TEST_ASSERT_TRUE(min_val < MP_OSC_DC_OFFSET);
    TEST_ASSERT_TRUE(max_val > MP_OSC_DC_OFFSET);
}

static void test_osc_volume_zero_is_silent(void) {
    mp_osc_init();
    mp_osc_set_freq(0, 1000);
    mp_osc_set_vol(0, 0);

    /* All samples should be DC offset */
    for (int i = 0; i < 100; i++) {
        uint16_t s = mp_osc_mix_sample();
        TEST_ASSERT_EQUAL(MP_OSC_DC_OFFSET, s);
    }
}

static void test_osc_volume_clamp(void) {
    mp_osc_init();
    /* Set volume above max */
    mp_osc_set_vol(0, 200);
    struct mp_osc_params* p = mp_osc_get_params(0);
    TEST_ASSERT_EQUAL(MP_OSC_MAX_VOLUME, p->vol);
}

/* --- Multi-channel mixing tests --- */

static void test_osc_multichannel_no_overflow(void) {
    mp_osc_init();
    /* Set all channels to max volume */
    for (uint8_t i = 0; i < MP_OSC_CH_COUNT; i++) {
        mp_osc_set_vol(i, MP_OSC_MAX_VOLUME);
        mp_osc_set_freq(i, 500 + i * 200);
    }

    /* Generate samples and verify no overflow */
    for (int i = 0; i < 2000; i++) {
        uint16_t s = mp_osc_mix_sample();
        TEST_ASSERT_IN_RANGE(s, 0, 1023);
    }
}

static void test_osc_multichannel_symmetry(void) {
    mp_osc_init();
    /* Two channels at same volume should produce symmetric output around DC */
    mp_osc_set_vol(0, 64);
    mp_osc_set_freq(0, 800);
    mp_osc_set_vol(1, 64);
    mp_osc_set_freq(1, 1200);

    int64_t sum = 0;
    int count = 4000;
    for (int i = 0; i < count; i++) {
        sum += (int16_t)mp_osc_mix_sample() - MP_OSC_DC_OFFSET;
    }

    /* Average should be close to 0 (DC offset centered) */
    int64_t avg = sum / count;
    TEST_ASSERT_IN_RANGE(avg, -20, 20);
}

/* --- Noise channel tests --- */

static void test_osc_noise_channel_produces_variation(void) {
    mp_osc_init();
    mp_osc_set_vol(MP_OSC_NOISE_CH, 64);

    /* Noise should produce varying output */
    uint16_t first = mp_osc_mix_sample();
    int different_count = 0;
    for (int i = 0; i < 100; i++) {
        uint16_t s = mp_osc_mix_sample();
        if (s != first) {
            different_count++;
        }
    }
    /* Noise should produce at least some different values */
    TEST_ASSERT_TRUE(different_count > 10);
}

/* --- Silence test --- */

static void test_osc_silence_all(void) {
    mp_osc_init();
    /* Set some channels active */
    mp_osc_set_vol(0, 100);
    mp_osc_set_freq(0, 1000);
    mp_osc_set_vol(1, 80);
    mp_osc_set_freq(1, 2000);

    /* Silence all */
    mp_osc_silence();

    /* Should output DC offset */
    for (int i = 0; i < 100; i++) {
        uint16_t s = mp_osc_mix_sample();
        TEST_ASSERT_EQUAL(MP_OSC_DC_OFFSET, s);
    }
}

/* --- Invalid channel tests --- */

static void test_osc_invalid_channel(void) {
    mp_osc_init();
    /* Should not crash with invalid channel */
    mp_osc_set_vol(MP_OSC_CH_COUNT, 100);
    mp_osc_set_freq(MP_OSC_CH_COUNT, 1000);
    mp_osc_set_mod(MP_OSC_CH_COUNT, 128);

    struct mp_osc_params* p = mp_osc_get_params(MP_OSC_CH_COUNT);
    TEST_ASSERT_NULL(p);
}

/* --- Frequency test --- */

static void test_osc_frequency_changes_output(void) {
    mp_osc_init();
    mp_osc_set_vol(0, 64);

    /* Low frequency */
    mp_osc_set_freq(0, 100);
    uint16_t low_samples[32];
    for (int i = 0; i < 32; i++) {
        low_samples[i] = mp_osc_mix_sample();
    }

    /* High frequency */
    mp_osc_init();
    mp_osc_set_vol(0, 64);
    mp_osc_set_freq(0, 5000);
    uint16_t high_samples[32];
    for (int i = 0; i < 32; i++) {
        high_samples[i] = mp_osc_mix_sample();
    }

    /* Count transitions (changes between high/low) */
    int low_transitions = 0;
    int high_transitions = 0;
    for (int i = 1; i < 32; i++) {
        if (low_samples[i] != low_samples[i - 1])
            low_transitions++;
        if (high_samples[i] != high_samples[i - 1])
            high_transitions++;
    }

    /* Higher frequency should have more transitions */
    TEST_ASSERT_TRUE(high_transitions >= low_transitions);
}

/* --- Test suite entry --- */

void test_osc_run(void) {
    TEST_SUITE_BEGIN("Oscillator Tests");

    RUN_TEST(test_osc_init_silence);
    RUN_TEST(test_osc_init_default_mod);
    RUN_TEST(test_osc_single_channel_output_range);
    RUN_TEST(test_osc_volume_zero_is_silent);
    RUN_TEST(test_osc_volume_clamp);
    RUN_TEST(test_osc_multichannel_no_overflow);
    RUN_TEST(test_osc_multichannel_symmetry);
    RUN_TEST(test_osc_noise_channel_produces_variation);
    RUN_TEST(test_osc_silence_all);
    RUN_TEST(test_osc_invalid_channel);
    RUN_TEST(test_osc_frequency_changes_output);

    TEST_SUITE_END();
}
