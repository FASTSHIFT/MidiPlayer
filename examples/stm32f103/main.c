/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer STM32F103 Example - Main Entry
 *
 * Plays a demo melody through PWM audio output on PB6.
 * Connect PB6 -> R(1kΩ) -> audio out, with C(10nF) to GND for filtering.
 */
#include "mp_player.h"
#include "port_stm32f103.h"
#include "midi_data.h"
#include "Arduino.h"

int main(void) {
    /* Initialize MCU core (NVIC, SysTick) */
    Core_Init();

    /* Initialize MidiPlayer library */
    mp_init();

    /* Initialize audio hardware (TIM3 + TIM4) */
    audio_hw_init();

    /* Start playing demo score */
    mp_play(&demo_score);

    /* Main loop - sequencer is driven by TIM3 ISR */
    while (1) {
        /* LED blink or other tasks can go here */
        if (!mp_is_playing()) {
            /* Restart when done */
            delay_ms(1000);
            mp_play(&demo_score);
        }
        delay_ms(100);
    }
}
