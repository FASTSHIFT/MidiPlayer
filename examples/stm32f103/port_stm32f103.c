/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer STM32F103 port implementation
 *
 * TIM2_CH1 (PA0): 10-bit PWM output at ~70.3kHz
 * TIM3: 16kHz sample rate interrupt driving the synthesizer
 */
#include "port_stm32f103.h"
#include "mp_player.h"
#include "Arduino.h"

/* PWM output pin */
#define AUDIO_PWM_PIN PA0
#define AUDIO_PWM_ARR 1023

/* Sample rate timer */
#define AUDIO_SR_TIM TIM3

/* Prescaler counter for sequencer tick (16kHz / 8 = 2kHz) */
static uint8_t prescaler_count = MP_OSC_PRESCALER_DIV;

/* 16kHz sample rate ISR */
static void audio_sample_isr(void) {
    analogWrite(AUDIO_PWM_PIN, mp_audio_tick());

    if (--prescaler_count == 0) {
        prescaler_count = MP_OSC_PRESCALER_DIV;
        mp_update(millis());
    }
}

void audio_hw_init(void) {
    /* Configure PWM: ARR=1023 (10-bit), PSC=0 -> 72MHz/1024 ≈ 70.3kHz */
    PWM_Init(AUDIO_PWM_PIN, MP_OSC_DC_OFFSET, 72000000 / (AUDIO_PWM_ARR + 1));

    /* Configure TIM3 as 16kHz sample rate interrupt (62.5us period) */
    Timer_SetInterrupt(AUDIO_SR_TIM, 1000000 / MP_OSC_SAMPLE_RATE, audio_sample_isr);
    Timer_SetEnable(AUDIO_SR_TIM, true);
}
