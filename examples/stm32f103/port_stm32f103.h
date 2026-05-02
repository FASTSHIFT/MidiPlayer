/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer STM32F103 port - Hardware abstraction
 *
 * TIM4_CH1 (PB6): PWM audio output (~70kHz, 10-bit)
 * TIM3: 16kHz sample rate interrupt
 */
#ifndef PORT_STM32F103_H
#define PORT_STM32F103_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief  Initialize audio hardware (TIM3 interrupt + TIM4 PWM)
 */
void audio_hw_init(void);

#ifdef __cplusplus
}
#endif

#endif /* PORT_STM32F103_H */
