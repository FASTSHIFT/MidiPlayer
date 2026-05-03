"""
Mixer — 4-channel integer mixing with DC offset.

Port of the mixing logic from source/mp_osc.c.
"""

import numpy as np

DC_OFFSET = 512
NUM_CHANNELS = 4  # 3 melodic + 1 noise


class Mixer:
    """Mix multiple oscillator outputs into a single 10-bit stream."""

    def __init__(self):
        self.last_output = None

    def mix(self, channel_samples):
        """
        Mix channel sample arrays into a single output.

        Args:
            channel_samples: list of int16 numpy arrays (one per channel)

        Returns:
            uint16 numpy array, range 0~1023
        """
        if not channel_samples:
            return np.full(1, DC_OFFSET, dtype=np.uint16)

        # All arrays must be same length
        n = len(channel_samples[0])
        mixed = np.full(n, DC_OFFSET, dtype=np.int32)

        for samples in channel_samples:
            mixed += samples.astype(np.int32)

        # Clamp to 10-bit range
        mixed = np.clip(mixed, 0, 1023).astype(np.uint16)
        self.last_output = mixed
        return mixed

    @staticmethod
    def to_float32(samples_10bit):
        """Convert 10-bit samples to float32 [-1.0, 1.0] for audio output."""
        return (samples_10bit.astype(np.float32) - DC_OFFSET) / DC_OFFSET
