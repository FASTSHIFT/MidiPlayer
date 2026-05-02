/*
 * MIT License
 * Copyright (c) 2026 VIFEX
 *
 * MidiPlayer STM32F103 Example
 *
 * PWM audio output on PA0. Use tools/load_midi.sh to convert and flash any MIDI.
 */
#include <Arduino.h>

extern "C" {
#include "mp_player.h"
#include "port_stm32f103.h"
#include "midi_data.h"
}

#define BUZZER_PIN PA0

static void buzzer_test(void) {
    Serial.println("Buzzer test...");
    pinMode(BUZZER_PIN, OUTPUT);

    tone(BUZZER_PIN, 523);
    delay(300);
    noTone(BUZZER_PIN);
    delay(100);

    tone(BUZZER_PIN, 1047);
    delay(300);
    noTone(BUZZER_PIN);

    Serial.println("Buzzer test done.\n");
    delay(300);
}

int main(void) {
    Core_Init();
    Serial.begin(115200);

    Serial.println("\n========================================");
    Serial.println("  MidiPlayer STM32F103");
    Serial.println("========================================");
    Serial.printf("Tracks: %d\r\n", midi_score.track_count);
    for (uint8_t i = 0; i < midi_score.track_count; i++) {
        Serial.printf("  Track %d: %lu events\r\n", i, (unsigned long)midi_score.tracks[i].event_count);
    }

    buzzer_test();

    Serial.println("Initializing MidiPlayer...");
    mp_init();
    audio_hw_init();

    Serial.println("Playing...\n");
    mp_play(&midi_score);

    Serial.printf("Duration: %lu ms\r\n\r\n", (unsigned long)mp_get_total_ms());

    uint32_t last_print = 0;
    while (1) {
        uint32_t now = millis();

        if (now - last_print >= 1000) {
            last_print = now;
            if (mp_is_playing()) {
                uint32_t elapsed = mp_get_elapsed_ms();
                uint32_t total = mp_get_total_ms();
                uint8_t pct = mp_get_progress_pct();
                Serial.printf("[%3d%%] %lu / %lu ms\r\n", pct, (unsigned long)elapsed, (unsigned long)total);
            }
        }

        if (!mp_is_playing()) {
            Serial.println("\nPlayback finished, restarting in 2s...\n");
            delay(2000);
            mp_play(&midi_score);
        }

        delay(50);
    }
}
