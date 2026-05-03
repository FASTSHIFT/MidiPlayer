"""Tests for player.visualizer — waveform display helpers."""

import numpy as np
from player.visualizer import phase_inc_to_note_name, Visualizer, NUM_CHANNELS
from player.sequencer import Sequencer


class TestNoteNameConversion:
    def test_a4(self):
        assert phase_inc_to_note_name(1802) == "A4"

    def test_c4(self):
        assert phase_inc_to_note_name(1072) == "C4"

    def test_zero(self):
        assert phase_inc_to_note_name(0) == "---"

    def test_very_low(self):
        assert phase_inc_to_note_name(1) == "---"


class TestVisualizerBuffers:
    def test_update_buffers_all_channels(self):
        seq = Sequencer()
        vis = Visualizer(seq)

        # 4 channels: 3 melodic + 1 noise
        ch_data = [np.full(100, 50, dtype=np.int16) for _ in range(NUM_CHANNELS)]
        mix_data = np.full(100, 512, dtype=np.uint16)

        vis.update_buffers(ch_data, mix_data)

        for i in range(NUM_CHANNELS):
            assert vis._ch_buffers[i][-1] == 50
        assert vis._mix_buffer[-1] == 512

    def test_buffer_rolls(self):
        seq = Sequencer()
        vis = Visualizer(seq)

        for val in [10, 20]:
            ch_data = [np.full(100, val, dtype=np.int16) for _ in range(NUM_CHANNELS)]
            mix_data = np.full(100, 500 + val, dtype=np.uint16)
            vis.update_buffers(ch_data, mix_data)

        for i in range(NUM_CHANNELS):
            assert vis._ch_buffers[i][-1] == 20
        assert vis._mix_buffer[-1] == 520

    def test_num_plots(self):
        seq = Sequencer()
        vis = Visualizer(seq)
        # 4 channels + 1 MIX = 5 subplots
        assert vis.num_plots == NUM_CHANNELS + 1

    def test_partial_channels(self):
        """update_buffers handles fewer channels than expected."""
        seq = Sequencer()
        vis = Visualizer(seq)

        # Only pass 2 channels instead of 4
        ch_data = [np.full(100, 42, dtype=np.int16) for _ in range(2)]
        mix_data = np.full(100, 512, dtype=np.uint16)

        vis.update_buffers(ch_data, mix_data)
        assert vis._ch_buffers[0][-1] == 42
        assert vis._ch_buffers[1][-1] == 42
        # Channels 2 and 3 should remain zero
        assert vis._ch_buffers[2][-1] == 0
        assert vis._ch_buffers[3][-1] == 0
