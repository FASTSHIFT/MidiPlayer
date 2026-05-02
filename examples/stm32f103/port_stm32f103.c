/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer STM32F103 port implementation
 *
 * TIM4_CH1 (PB6): 10-bit PWM output at ~70.3kHz
 * TIM3: 16kHz sample rate interrupt driving the oscillator
 */
#include "port_stm32f103.h"
#include "mp_player.h"
#include "mp_port.h"
#include "Arduino.h"

/* PWM configuration: 72MHz / 1024 ≈ 70.3kHz, 10-bit resolution */
#define AUDIO_PWM_TIM TIM4
#define AUDIO_PWM_ARR 1023
#define AUDIO_PWM_PIN PB6

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
    /* Generate mixed audio sample and output to PWM */
    uint16_t sample = mp_audio_tick();
    mp_port_audio_write(sample);

    /* Prescaler: run sequencer at 2kHz (every 8 samples) */
    if (--prescaler_count == 0) {
        prescaler_count = 8;
        mp_update(mp_port_get_tick_ms());
    }
}

void audio_hw_init(void) {
    /* Initialize TIM4_CH1 as PWM output on PB6 */
    /* ARR = 1023 (10-bit), PSC = 0, freq = 72MHz/1024 ≈ 70.3kHz */
    PWM_Init(AUDIO_PWM_PIN, AUDIO_PWM_ARR + 1, 72000000 / (AUDIO_PWM_ARR + 1));

    /* Set initial duty to DC offset (silence) */
    mp_port_audio_write(MP_OSC_DC_OFFSET);

    /* Initialize TIM3 as 16kHz sample rate interrupt */
    /* 72MHz / 16000 = 4500 ticks per interrupt */
    Timer_SetInterruptBase(AUDIO_SR_TIM, 4500,  /* period */
                           1,                   /* prescaler (div by 1) */
                           audio_sample_isr, 0, /* highest preemption priority */
                           0                    /* highest sub priority */
    );
}
