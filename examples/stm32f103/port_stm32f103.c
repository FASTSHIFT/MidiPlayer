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

/*
 * PWM resolution: 1024 levels (10-bit)
 * PWM_Init(pin, resolution, frequency):
 *   ARR = resolution - 1 = 1023
 *   PSC = F_CPU / resolution / frequency - 1
 *   -> 72MHz / 1024 / 70312 ≈ 0 -> PSC=0, actual freq = 72MHz/1024 ≈ 70.3kHz
 */
#define AUDIO_PWM_RESOLUTION (1 << MP_OSC_PWM_BITS) /* 1024 */
#define AUDIO_PWM_FREQUENCY  (F_CPU / AUDIO_PWM_RESOLUTION) /* ~70.3kHz */

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
    PWM_Init(AUDIO_PWM_PIN, AUDIO_PWM_RESOLUTION, AUDIO_PWM_FREQUENCY);

    /* Set initial duty to DC offset (silence) */
    analogWrite(AUDIO_PWM_PIN, MP_OSC_DC_OFFSET);

    /* Configure TIM3 as 16kHz sample rate interrupt */
    Timer_SetInterrupt(AUDIO_SR_TIM, 1000000 / MP_OSC_SAMPLE_RATE, audio_sample_isr);
    Timer_SetEnable(AUDIO_SR_TIM, true);
}
