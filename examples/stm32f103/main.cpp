/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer STM32F103 Example
 *
 * Plays Pirates of the Caribbean through PWM audio output on PA0.
 */
#include <Arduino.h>

extern "C" {
#include "mp_player.h"
#include "port_stm32f103.h"
#include "midi_data.h"
}

#define BUZZER_PIN PA0

/* Quick buzzer test: play a few notes using tone() to verify hardware */
static void buzzer_test(void) {
    Serial.println("Buzzer test on PA0...");
    pinMode(BUZZER_PIN, OUTPUT);

    Serial.println("  C5 (523Hz)");
    tone(BUZZER_PIN, 523);
    delay(300);
    noTone(BUZZER_PIN);
    delay(100);

    Serial.println("  E5 (659Hz)");
    tone(BUZZER_PIN, 659);
    delay(300);
    noTone(BUZZER_PIN);
    delay(100);

    Serial.println("  G5 (784Hz)");
    tone(BUZZER_PIN, 784);
    delay(300);
    noTone(BUZZER_PIN);
    delay(100);

    Serial.println("  C6 (1047Hz)");
    tone(BUZZER_PIN, 1047);
    delay(500);
    noTone(BUZZER_PIN);

    Serial.println("Buzzer test done.\n");
    delay(500);
}

int main(void) {
    Core_Init();
    Serial.begin(115200);

    Serial.println("\n========================================");
    Serial.println("  MidiPlayer STM32F103");
    Serial.println("========================================");
    Serial.printf("Score: Pirates of the Caribbean\r\n");
    Serial.printf("Tracks: %d\r\n", pirates_score.track_count);
    for (uint8_t i = 0; i < pirates_score.track_count; i++) {
        Serial.printf("  Track %d: %lu events\r\n", i, (unsigned long)pirates_score.tracks[i].event_count);
    }

    /* Step 1: Test buzzer with tone() */
    buzzer_test();

    /* Step 2: Init MidiPlayer and start PWM playback */
    Serial.println("PWM: PA0 (TIM2_CH1), ~70kHz 10-bit");
    Serial.println("Sample rate: 16kHz (TIM3)");

    mp_init();
    Serial.println("mp_init() done");

    audio_hw_init();
    Serial.println("audio_hw_init() done");

    mp_play(&pirates_score);
    Serial.println("mp_play() started");

    uint32_t last_print = 0;
    while (1) {
        uint32_t now = millis();
        if (now - last_print >= 2000) {
            last_print = now;
            Serial.printf("[%lu ms] playing=%d\r\n", (unsigned long)now, mp_is_playing());
        }

        if (!mp_is_playing()) {
            Serial.println("Playback finished, restarting in 1s...");
            delay_ms(1000);
            mp_play(&pirates_score);
            Serial.println("mp_play() restarted");
        }
        delay_ms(100);
    }
}
