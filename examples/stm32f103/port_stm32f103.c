/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer STM32F103 port implementation
 *
 * TIM2_CH1 (PA0): 10-bit PWM output at ~70.3kHz
 * TIM3: 16kHz sample rate interrupt driving the oscillator
 */
#include "port_stm32f103.h"
#include "mp_player.h"
#include "mp_port.h"
#include "Arduino.h"

/* PWM: TIM2_CH1 on PA0, ARR=1023 (10-bit), PSC=0 -> 72MHz/1024 ≈ 70.3kHz */
#define AUDIO_PWM_TIM TIM2
#define AUDIO_PWM_ARR 1023
#define AUDIO_PWM_PIN PA0

/* Sample rate timer */
#define AUDIO_SR_TIM TIM3

/* Prescaler counter for sequencer tick */
static uint8_t prescaler_count = 8;

/* Platform callbacks */

static void stm32_audio_write(uint16_t value) {
    AUDIO_PWM_TIM->CCR1 = value;
}

static uint32_t stm32_get_tick(void) {
    return millis();
}

/* 16kHz sample rate ISR */
static void audio_sample_isr(void) {
    uint16_t sample = mp_audio_tick();
    mp_port_audio_write(sample);

    if (--prescaler_count == 0) {
        prescaler_count = 8;
        mp_update(mp_port_get_tick_ms());
    }
}

void audio_hw_init(void) {
    /* Register platform callbacks */
    mp_port_t port = {
        .audio_write = stm32_audio_write,
        .get_tick_ms = stm32_get_tick,
    };
    mp_port_init(&port);

    /* Configure PA0 as TIM2_CH1 alternate function push-pull */
    pinMode(AUDIO_PWM_PIN, OUTPUT_AF);

    /* Configure TIM2 for PWM: ARR=1023, PSC=0 -> 72MHz/1024 ≈ 70.3kHz */
    TIMx_OCxInit(AUDIO_PWM_TIM, AUDIO_PWM_ARR, 0, PIN_MAP[AUDIO_PWM_PIN].TimerChannel);

    /* Set initial duty to DC offset (silence) */
    mp_port_audio_write(MP_OSC_DC_OFFSET);

    /* Configure TIM3 as 16kHz sample rate interrupt (62.5us period) */
    Timer_SetInterrupt(AUDIO_SR_TIM, 1000000 / 16000, audio_sample_isr);
    Timer_SetEnable(AUDIO_SR_TIM, true);
}
