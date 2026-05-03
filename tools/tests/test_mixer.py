"""Tests for player.mixer — multi-channel mixing."""

import numpy as np
import pytest
from player.mixer import Mixer, DC_OFFSET, NUM_CHANNELS


class TestMixer:
    def test_silence_is_dc_offset(self):
        mixer = Mixer()
        zeros = [np.zeros(100, dtype=np.int16) for _ in range(NUM_CHANNELS)]
        out = mixer.mix(zeros)
        assert np.all(out == DC_OFFSET)

    def test_single_channel(self):
        mixer = Mixer()
        ch = np.full(100, 64, dtype=np.int16)
        zeros = [np.zeros(100, dtype=np.int16) for _ in range(NUM_CHANNELS - 1)]
        out = mixer.mix([ch] + zeros)
        assert np.all(out == DC_OFFSET + 64)

    def test_no_overflow(self):
        mixer = Mixer()
        maxvol = np.full(100, 127, dtype=np.int16)
        out = mixer.mix([maxvol] * NUM_CHANNELS)
        assert out.max() <= 1023
        assert out.min() >= 0

    def test_no_underflow(self):
        mixer = Mixer()
        minvol = np.full(100, -127, dtype=np.int16)
        out = mixer.mix([minvol] * NUM_CHANNELS)
        assert out.min() >= 0
        assert out.max() <= 1023

    def test_to_float32_range(self):
        samples = np.array([0, 512, 1023], dtype=np.uint16)
        f = Mixer.to_float32(samples)
        assert f[0] == pytest.approx(-1.0, abs=0.01)
        assert f[1] == pytest.approx(0.0, abs=0.01)
        assert f[2] == pytest.approx(1.0, abs=0.01)

    def test_empty_input(self):
        mixer = Mixer()
        out = mixer.mix([])
        assert len(out) == 1
        assert out[0] == DC_OFFSET

    def test_num_channels_is_8(self):
        assert NUM_CHANNELS == 8

    def test_8_channels_moderate_volume(self):
        """8 channels at moderate volume should not clip."""
        mixer = Mixer()
        moderate = np.full(100, 60, dtype=np.int16)
        out = mixer.mix([moderate] * NUM_CHANNELS)
        # 512 + 8*60 = 992, should not clip
        assert np.all(out == DC_OFFSET + 60 * NUM_CHANNELS)
