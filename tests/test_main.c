/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer test runner entry point
 */
#include "test_framework.h"

/* Test suite declarations */
extern void test_osc_run(void);
extern void test_note_table_run(void);
extern void test_sequencer_run(void);
extern void test_player_run(void);

int main(void) {
    test_framework_init();

    test_osc_run();
    test_note_table_run();
    test_sequencer_run();
    test_player_run();

    return test_framework_report();
}
