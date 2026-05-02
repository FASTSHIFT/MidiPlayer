/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * Unit tests for mp_note_table
 */
#include "test_framework.h"
#include "mp_note_table.h"

static void test_note_a4_frequency(void) {
    /* A4 = MIDI note 69, freq = 440Hz
       phase_inc = 440 * 65536 / 16000 = 1802.24 ≈ 1802 */
    uint16_t inc = mp_note_to_phase_inc(69);
    TEST_ASSERT_EQUAL(1802, inc);
}

static void test_note_c4_frequency(void) {
    /* C4 = MIDI note 60, freq = 261.63Hz
       phase_inc = 261.63 * 65536 / 16000 = 1072 */
    uint16_t inc = mp_note_to_phase_inc(60);
    TEST_ASSERT_EQUAL(1072, inc);
}

static void test_note_out_of_range_low(void) {
    /* Notes below 24 should return 0 */
    TEST_ASSERT_EQUAL(0, mp_note_to_phase_inc(0));
    TEST_ASSERT_EQUAL(0, mp_note_to_phase_inc(23));
}

static void test_note_out_of_range_high(void) {
    /* Notes above 108 should return 0 */
    TEST_ASSERT_EQUAL(0, mp_note_to_phase_inc(109));
    TEST_ASSERT_EQUAL(0, mp_note_to_phase_inc(127));
}

static void test_note_boundary_valid(void) {
    /* Note 24 (C1) and 108 (C8) should be valid */
    TEST_ASSERT_NOT_EQUAL(0, mp_note_to_phase_inc(24));
    TEST_ASSERT_NOT_EQUAL(0, mp_note_to_phase_inc(108));
}

static void test_note_monotonic_increase(void) {
    /* Phase increments should increase with note number */
    uint16_t prev = 0;
    for (uint8_t note = 24; note <= 108; note++) {
        uint16_t inc = mp_note_to_phase_inc(note);
        TEST_ASSERT_TRUE(inc > prev);
        prev = inc;
    }
}

static void test_note_octave_doubling(void) {
    /* An octave up should roughly double the phase increment */
    for (uint8_t note = 24; note <= 96; note += 12) {
        uint16_t low = mp_note_to_phase_inc(note);
        uint16_t high = mp_note_to_phase_inc(note + 12);
        /* Allow 2% tolerance for rounding */
        int32_t ratio_x100 = (int32_t)high * 100 / low;
        TEST_ASSERT_IN_RANGE(ratio_x100, 195, 205);
    }
}

static void test_note_table_size(void) {
    /* Should cover 85 notes (24..108 inclusive) */
    TEST_ASSERT_EQUAL(85, mp_note_table_size());
}

void test_note_table_run(void) {
    TEST_SUITE_BEGIN("Note Table Tests");

    RUN_TEST(test_note_a4_frequency);
    RUN_TEST(test_note_c4_frequency);
    RUN_TEST(test_note_out_of_range_low);
    RUN_TEST(test_note_out_of_range_high);
    RUN_TEST(test_note_boundary_valid);
    RUN_TEST(test_note_monotonic_increase);
    RUN_TEST(test_note_octave_doubling);
    RUN_TEST(test_note_table_size);

    TEST_SUITE_END();
}
