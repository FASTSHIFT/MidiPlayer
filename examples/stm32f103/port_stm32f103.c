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

/* mp_port.h implementation */

void mp_port_audio_write(uint16_t value) {
    AUDIO_PWM_TIM->CCR1 = value;
}

uint32_t mp_port_get_tick_ms(void) {
    return millis();
}

/* 16kHz sample rate ISR */
static void audio_sample_isr(void) {
    uint16_t sample = mp_audio_tick();
    mp_port_audio_write(sample);

    /* Prescaler: run sequencer at 2kHz (every 8 samples) */
    if (--prescaler_count == 0) {
        prescaler_count = 8;
        mp_update(mp_port_get_tick_ms());
    }
}

void audio_hw_init(void) {
    /* Configure PA0 as TIM2_CH1 alternate function push-pull */
    pinMode(AUDIO_PWM_PIN, OUTPUT_AF);

    /* Configure TIM2 for PWM: ARR=1023, PSC=0 -> 72MHz/1024 ≈ 70.3kHz */
    TIMx_OCxInit(AUDIO_PWM_TIM, AUDIO_PWM_ARR, 0, PIN_MAP[AUDIO_PWM_PIN].TimerChannel);

    /* Set initial duty to DC offset (silence) */
    mp_port_audio_write(MP_OSC_DC_OFFSET);

    /* Configure TIM3 as 16kHz sample rate interrupt */
    /* period=4500, prescaler=1 -> 72MHz / (4500 * 1) = 16kHz */
    Timer_SetInterruptBase(AUDIO_SR_TIM, 4500,  /* period */
                           1,                   /* prescaler */
                           audio_sample_isr, 0, /* preemption priority (highest) */
                           0                    /* sub priority */
    );
    Timer_SetEnable(AUDIO_SR_TIM, true);
}
