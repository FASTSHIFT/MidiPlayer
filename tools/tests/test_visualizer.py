"""Tests for player.visualizer — waveform display helpers."""

import numpy as np
from player.visualizer import phase_inc_to_note_name, Visualizer
from player.sequencer import Sequencer


class TestNoteNameConversion:
    def test_a4(self):
        assert phase_inc_to_note_name(1802) == " A4"

    def test_c4(self):
        assert phase_inc_to_note_name(1072) == " C4"

    def test_zero(self):
        assert phase_inc_to_note_name(0) == "---"

    def test_very_low(self):
        assert phase_inc_to_note_name(1) == "---"


class TestVisualizerBuffers:
    def test_update_buffers_all_channels(self):
        seq = Sequencer()
        vis = Visualizer(seq)
        n = seq.num_channels

        ch_data = [np.full(100, 50, dtype=np.int16) for _ in range(n)]
        mix_data = np.full(100, 512, dtype=np.uint16)

        vis.update_buffers(ch_data, mix_data)

        for i in range(n):
            assert vis._ch_buffers[i][-1] == 50
        assert vis._mix_buffer[-1] == 512

    def test_buffer_rolls(self):
        seq = Sequencer()
        vis = Visualizer(seq)
        n = seq.num_channels

        for val in [10, 20]:
            ch_data = [np.full(100, val, dtype=np.int16) for _ in range(n)]
            mix_data = np.full(100, 500 + val, dtype=np.uint16)
            vis.update_buffers(ch_data, mix_data)

        for i in range(n):
            assert vis._ch_buffers[i][-1] == 20
        assert vis._mix_buffer[-1] == 520

    def test_num_plots(self):
        seq = Sequencer()
        vis = Visualizer(seq)
        assert vis.num_plots == seq.num_channels + 1

    def test_partial_channels(self):
        """update_buffers handles fewer channels than expected."""
        seq = Sequencer()
        vis = Visualizer(seq)

        ch_data = [np.full(100, 42, dtype=np.int16) for _ in range(2)]
        mix_data = np.full(100, 512, dtype=np.uint16)

        vis.update_buffers(ch_data, mix_data)
        assert vis._ch_buffers[0][-1] == 42
        assert vis._ch_buffers[1][-1] == 42
        # Remaining channels should stay zero
        for i in range(2, seq.num_channels):
            assert vis._ch_buffers[i][-1] == 0

    def test_seeking_flag_default(self):
        seq = Sequencer()
        vis = Visualizer(seq)
        assert vis._seeking is False


class TestWaveformSymbols:
    def test_symbols_defined(self):
        from player.visualizer import WAVEFORM_SYMBOLS

        assert len(WAVEFORM_SYMBOLS) == 4
        assert "SQR" in WAVEFORM_SYMBOLS[0]
        assert "TRI" in WAVEFORM_SYMBOLS[1]
        assert "SAW" in WAVEFORM_SYMBOLS[2]
        assert "PLS" in WAVEFORM_SYMBOLS[3]

    def test_adsr_colors_defined(self):
        from player.visualizer import ADSR_ACTIVE_COLORS

        assert len(ADSR_ACTIVE_COLORS) == 4

    def test_adsr_stage_names(self):
        from player.visualizer import ADSR_STAGE_NAMES

        assert len(ADSR_STAGE_NAMES) == 4
        assert "Atk" in ADSR_STAGE_NAMES[0]
        assert "Dec" in ADSR_STAGE_NAMES[1]
        assert "Sus" in ADSR_STAGE_NAMES[2]
        assert "Rel" in ADSR_STAGE_NAMES[3]

    def test_speed_options(self):
        from player.visualizer import SPEED_OPTIONS

        assert 1.0 in SPEED_OPTIONS
        assert all(s > 0 for s in SPEED_OPTIONS)


class TestAdaptiveColors:
    """Tests for auto-generated channel colors."""

    def test_default_sequencer_uses_preset_colors(self):
        """Default 8-channel sequencer should be covered by preset colors."""
        seq = Sequencer()
        assert seq.num_channels <= 8

    def test_num_plots_matches_channels(self):
        seq = Sequencer()
        vis = Visualizer(seq)
        assert vis.num_plots == seq.num_channels + 1
        assert vis.num_channels == seq.num_channels
        assert len(vis._ch_buffers) == seq.num_channels

    def test_visualizer_adapts_to_small_sequencer(self):
        """Visualizer should adapt to a 2-channel sequencer."""
        seq = Sequencer(num_melodic=1)
        assert seq.num_channels == 2
        vis = Visualizer(seq)
        assert vis.num_channels == 2
        assert vis.num_plots == 3
        assert len(vis._ch_buffers) == 2

    def test_visualizer_adapts_to_large_sequencer(self):
        """Visualizer should adapt to a 16-channel sequencer (colormap fallback)."""
        seq = Sequencer(num_melodic=15)
        assert seq.num_channels == 16
        vis = Visualizer(seq)
        assert vis.num_channels == 16
        assert vis.num_plots == 17
        assert len(vis._ch_buffers) == 16
