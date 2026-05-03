"""
ADSR Envelope Generator — port of source/mp_envelope.c.

Linear four-stage envelope running at 2kHz tick rate.
Same presets and state machine as the MCU implementation.
"""

from enum import IntEnum


class AdsrPreset(IntEnum):
    DEFAULT = 0
    PIANO = 1
    ORGAN = 2
    STRINGS = 3
    BASS = 4
    LEAD = 5
    PAD = 6


# Preset parameters: (attack, decay, sustain, release) in ticks at 2kHz
# sustain is 0~255 (fraction of peak: 255 = 100%)
ADSR_PRESETS = {
    AdsrPreset.DEFAULT: (10, 200, 200, 200),
    AdsrPreset.PIANO: (4, 800, 80, 400),
    AdsrPreset.ORGAN: (2, 0, 255, 100),
    AdsrPreset.STRINGS: (200, 0, 255, 600),
    AdsrPreset.BASS: (6, 400, 160, 200),
    AdsrPreset.LEAD: (8, 100, 220, 150),
    AdsrPreset.PAD: (400, 0, 255, 1000),
}


class Stage(IntEnum):
    IDLE = 0
    ATTACK = 1
    DECAY = 2
    SUSTAIN = 3
    RELEASE = 4


class Envelope:
    """Single-channel ADSR envelope."""

    def __init__(self):
        self.stage = Stage.IDLE
        self.counter = 0
        self.level = 0  # 0~127
        self.peak_vol = 0
        self.sustain_vol = 0
        self.attack = 10
        self.decay = 200
        self.sustain = 200
        self.release = 200

    def set_preset(self, preset):
        """Load ADSR parameters from preset."""
        if preset in ADSR_PRESETS:
            self.attack, self.decay, self.sustain, self.release = ADSR_PRESETS[preset]

    def set_adsr(self, attack, decay, sustain, release):
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release

    def note_on(self, velocity):
        """Trigger attack phase."""
        self.peak_vol = min(velocity, 127)
        self.sustain_vol = self.peak_vol * self.sustain // 255

        if self.attack > 0:
            self.stage = Stage.ATTACK
            self.counter = self.attack
            self.level = 0
        else:
            self.level = self.peak_vol
            if self.decay > 0:
                self.stage = Stage.DECAY
                self.counter = self.decay
            else:
                self.stage = Stage.SUSTAIN
                self.level = self.sustain_vol

    def note_off(self):
        """Trigger release phase."""
        if self.stage == Stage.IDLE:
            return
        if self.release > 0:
            self.stage = Stage.RELEASE
            self.counter = self.release
        else:
            self.stage = Stage.IDLE
            self.level = 0

    def tick(self):
        """Advance envelope by one tick. Call at 2kHz."""
        if self.stage == Stage.ATTACK:
            if self.counter > 0:
                elapsed = self.attack - self.counter
                self.level = self.peak_vol * elapsed // self.attack
                self.counter -= 1
            if self.counter == 0:
                self.level = self.peak_vol
                if self.decay > 0:
                    self.stage = Stage.DECAY
                    self.counter = self.decay
                else:
                    self.stage = Stage.SUSTAIN
                    self.level = self.sustain_vol

        elif self.stage == Stage.DECAY:
            if self.counter > 0:
                elapsed = self.decay - self.counter
                delta = self.peak_vol - self.sustain_vol
                self.level = self.peak_vol - delta * elapsed // self.decay
                self.counter -= 1
            if self.counter == 0:
                self.level = self.sustain_vol
                self.stage = Stage.SUSTAIN

        elif self.stage == Stage.SUSTAIN:
            self.level = self.sustain_vol

        elif self.stage == Stage.RELEASE:
            if self.counter > 0:
                elapsed = self.release - self.counter
                start_level = self.sustain_vol
                if elapsed < self.release:
                    self.level = start_level - start_level * elapsed // self.release
                else:
                    self.level = 0
                self.counter -= 1
            if self.counter == 0:
                self.level = 0
                self.stage = Stage.IDLE

        else:
            self.level = 0

        return self.level
