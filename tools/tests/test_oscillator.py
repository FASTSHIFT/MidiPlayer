"""Tests for player.oscillator — waveform generation."""

import numpy as np
from player.oscillator import Oscillator, NoiseChannel, Waveform, midi_note_to_phase_inc


class TestOscillator:
    def test_silence_when_vol_zero(self):
        osc = Oscillator()
        osc.set_freq(1000)
        osc.set_vol(0)
        samples = osc.generate(100)
        assert np.all(samples == 0)

    def test_silence_when_freq_zero(self):
        osc = Oscillator()
        osc.set_freq(0)
        osc.set_vol(100)
        samples = osc.generate(100)
        assert np.all(samples == 0)

    def test_square_wave_range(self):
        osc = Oscillator()
        osc.set_freq(1000)
        osc.set_vol(64)
        osc.set_waveform(Waveform.SQUARE)
        samples = osc.generate(500)
        assert samples.min() >= -64
        assert samples.max() <= 64
        # Should have both positive and negative
        assert samples.max() > 0
        assert samples.min() < 0

    def test_triangle_wave_smooth(self):
        osc = Oscillator()
        osc.set_freq(1000)
        osc.set_vol(64)
        osc.set_waveform(Waveform.TRIANGLE)
        samples = osc.generate(256)
        # Triangle should have many distinct values (smooth)
        unique = len(np.unique(samples))
        assert unique > 10

    def test_sawtooth_wave_range(self):
        osc = Oscillator()
        osc.set_freq(1000)
        osc.set_vol(64)
        osc.set_waveform(Waveform.SAWTOOTH)
        samples = osc.generate(500)
        assert samples.min() >= -64
        assert samples.max() <= 64

    def test_pulse25_duty_cycle(self):
        osc = Oscillator()
        osc.set_freq(1000)
        osc.set_vol(64)
        osc.set_waveform(Waveform.PULSE_25)
        samples = osc.generate(1000)
        high = np.sum(samples > 0)
        # ~25% should be high (allow tolerance)
        assert 100 < high < 500

    def test_volume_clamp(self):
        osc = Oscillator()
        osc.set_vol(200)
        assert osc.vol == 127

    def test_all_waveforms_valid_range(self):
        for wf in Waveform:
            osc = Oscillator()
            osc.set_freq(1000)
            osc.set_vol(127)
            osc.set_waveform(wf)
            samples = osc.generate(500)
            assert samples.min() >= -127
            assert samples.max() <= 127

    def test_silence_method(self):
        osc = Oscillator()
        osc.set_freq(1000)
        osc.set_vol(100)
        osc.silence()
        assert osc.vol == 0
        assert osc.phase_inc == 0


class TestNoiseChannel:
    def test_noise_produces_variation(self):
        noise = NoiseChannel()
        noise.set_vol(64)
        samples = noise.generate(100)
        unique = len(np.unique(samples))
        assert unique > 1

    def test_noise_silent_when_vol_zero(self):
        noise = NoiseChannel()
        noise.set_vol(0)
        samples = noise.generate(100)
        assert np.all(samples == 0)

    def test_noise_range(self):
        noise = NoiseChannel()
        noise.set_vol(64)
        samples = noise.generate(1000)
        assert samples.min() >= -64
        assert samples.max() <= 64


class TestNoteTable:
    def test_a4_phase_inc(self):
        # A4 = 440Hz, phase_inc = 440 * 65536 / 16000 = 1802
        assert midi_note_to_phase_inc(69) == 1802

    def test_c4_phase_inc(self):
        assert midi_note_to_phase_inc(60) == 1072

    def test_out_of_range(self):
        assert midi_note_to_phase_inc(0) == 0
        assert midi_note_to_phase_inc(23) == 0
        assert midi_note_to_phase_inc(109) == 0

    def test_monotonic(self):
        prev = 0
        for note in range(24, 109):
            inc = midi_note_to_phase_inc(note)
            assert inc > prev
            prev = inc

    def test_octave_doubling(self):
        for note in range(24, 97, 12):
            low = midi_note_to_phase_inc(note)
            high = midi_note_to_phase_inc(note + 12)
            ratio = high * 100 // low
            assert 195 <= ratio <= 205
