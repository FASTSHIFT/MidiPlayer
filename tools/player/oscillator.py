"""
Oscillator — Phase accumulator + multi-waveform synthesis.

Port of source/mp_osc.c to Python/numpy.
Numerically identical to the MCU implementation.
"""

import numpy as np
from enum import IntEnum

SAMPLE_RATE = 16000


class Waveform(IntEnum):
    SQUARE = 0
    TRIANGLE = 1
    SAWTOOTH = 2
    PULSE_25 = 3


class Oscillator:
    """Single-channel oscillator with phase accumulator."""

    def __init__(self):
        self.phase_acc = np.uint16(0)
        self.phase_inc = np.uint16(0)
        self.mod = np.uint8(127)  # 50% duty cycle
        self.vol = np.uint8(0)
        self.waveform = Waveform.SQUARE

    def set_freq(self, phase_inc):
        self.phase_inc = np.uint16(phase_inc)

    def set_vol(self, vol):
        self.vol = np.uint8(min(vol, 127))

    def set_mod(self, mod):
        self.mod = np.uint8(mod)

    def set_waveform(self, waveform):
        self.waveform = Waveform(waveform)

    def silence(self):
        self.vol = np.uint8(0)
        self.phase_inc = np.uint16(0)

    def generate(self, num_samples):
        """Generate num_samples of audio. Returns int16 array (range ±vol)."""
        if self.vol == 0 or self.phase_inc == 0:
            return np.zeros(num_samples, dtype=np.int16)

        # Vectorized phase accumulation (uint16 wrapping)
        offsets = np.arange(1, num_samples + 1, dtype=np.uint32)
        phases = np.uint16(self.phase_acc + offsets * self.phase_inc)
        self.phase_acc = phases[-1]

        phase_hi = (phases >> 8).astype(np.uint8)
        vol = int(self.vol)

        if self.waveform == Waveform.SQUARE:
            return np.where(phase_hi < self.mod, vol, -vol).astype(np.int16)

        elif self.waveform == Waveform.TRIANGLE:
            tri = np.where(
                phase_hi < 128,
                phase_hi.astype(np.int16) * 2 - 128,
                (255 - phase_hi).astype(np.int16) * 2 - 128,
            )
            return (tri * vol // 128).astype(np.int16)

        elif self.waveform == Waveform.SAWTOOTH:
            saw = phase_hi.astype(np.int16) - 128
            return (saw * vol // 128).astype(np.int16)

        elif self.waveform == Waveform.PULSE_25:
            return np.where(phase_hi < 64, vol, -vol).astype(np.int16)

        else:
            return np.where(phase_hi < self.mod, vol, -vol).astype(np.int16)


class NoiseChannel:
    """LFSR noise generator — port of MCU noise channel."""

    def __init__(self):
        self.lfsr = np.uint16(1)
        self.vol = np.uint8(0)

    def set_vol(self, vol):
        self.vol = np.uint8(min(vol, 127))

    def silence(self):
        self.vol = np.uint8(0)

    def generate(self, num_samples):
        """Generate noise samples. Per-sample LFSR (not vectorizable)."""
        if self.vol == 0:
            return np.zeros(num_samples, dtype=np.int16)

        out = np.empty(num_samples, dtype=np.int16)
        lfsr = int(self.lfsr)
        vol = int(self.vol)

        for i in range(num_samples):
            feedback = ((lfsr >> 15) ^ (lfsr >> 14)) & 1
            lfsr = ((lfsr << 1) | feedback) & 0xFFFF
            out[i] = vol if (lfsr & 0x8000) else -vol

        self.lfsr = np.uint16(lfsr)
        return out


def midi_note_to_phase_inc(note):
    """Convert MIDI note (0~127) to phase increment for 16kHz sample rate."""
    if note < 24 or note > 108:
        return 0
    freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
    return round(freq * 65536 / SAMPLE_RATE)
