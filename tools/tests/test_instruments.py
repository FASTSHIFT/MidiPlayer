"""Tests for player.instruments — GM instrument mapping."""

from player.instruments import get_instrument_params, MOD_50, MOD_25, MOD_12
from player.oscillator import Waveform
from player.envelope import AdsrPreset


class TestInstrumentMapping:
    def test_returns_tuple_of_three(self):
        for program in range(128):
            result = get_instrument_params(program)
            assert isinstance(result, tuple)
            assert len(result) == 3

    def test_mod_values_valid(self):
        valid_mods = {MOD_50, MOD_25, MOD_12}
        for program in range(128):
            mod, _, _ = get_instrument_params(program)
            assert mod in valid_mods, f"program {program}: mod={mod}"

    def test_adsr_presets_valid(self):
        for program in range(128):
            _, adsr, _ = get_instrument_params(program)
            assert (
                adsr in AdsrPreset.__members__.values()
            ), f"program {program}: adsr={adsr}"

    def test_waveforms_valid(self):
        for program in range(128):
            _, _, waveform = get_instrument_params(program)
            assert (
                waveform in Waveform.__members__.values()
            ), f"program {program}: waveform={waveform}"

    def test_piano_family(self):
        for program in range(8):
            mod, adsr, waveform = get_instrument_params(program)
            assert waveform == Waveform.TRIANGLE
            assert adsr == AdsrPreset.PIANO

    def test_organ_family(self):
        for program in range(16, 24):
            mod, adsr, waveform = get_instrument_params(program)
            assert adsr == AdsrPreset.ORGAN
            assert waveform == Waveform.SQUARE

    def test_strings_family(self):
        for program in range(40, 48):
            mod, adsr, waveform = get_instrument_params(program)
            assert adsr == AdsrPreset.STRINGS
            assert waveform == Waveform.SAWTOOTH

    def test_bass_family(self):
        for program in range(32, 40):
            mod, adsr, waveform = get_instrument_params(program)
            assert adsr == AdsrPreset.BASS

    def test_lead_family(self):
        for program in range(56, 64):
            _, adsr, _ = get_instrument_params(program)
            assert adsr == AdsrPreset.LEAD

    def test_pad_family(self):
        for program in range(88, 96):
            _, adsr, waveform = get_instrument_params(program)
            assert adsr == AdsrPreset.PAD
            assert waveform == Waveform.TRIANGLE

    def test_synth_lead_pulse(self):
        for program in range(80, 88):
            _, _, waveform = get_instrument_params(program)
            assert waveform == Waveform.PULSE_25

    def test_chromatic_percussion(self):
        for program in range(8, 16):
            mod, adsr, _ = get_instrument_params(program)
            assert mod == MOD_25
            assert adsr == AdsrPreset.PIANO

    def test_guitar_sawtooth(self):
        for program in range(24, 32):
            _, _, waveform = get_instrument_params(program)
            assert waveform == Waveform.SAWTOOTH

    def test_pipe_triangle(self):
        for program in range(72, 80):
            _, adsr, waveform = get_instrument_params(program)
            assert adsr == AdsrPreset.ORGAN
            assert waveform == Waveform.TRIANGLE

    def test_synth_effects(self):
        for program in range(96, 104):
            mod, _, _ = get_instrument_params(program)
            assert mod == MOD_12

    def test_sound_effects_fallback(self):
        mod, adsr, waveform = get_instrument_params(127)
        assert adsr == AdsrPreset.DEFAULT
        assert waveform == Waveform.SQUARE


class TestConverterConsistency:
    """Verify player.instruments matches midi_to_header.py mappings."""

    def test_all_programs_match_converter(self):
        """Ensure PC player uses same instrument mapping as the C converter."""
        # Import the converter's mapping function
        import importlib.util
        import os

        converter_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "midi_to_header.py",
        )
        spec = importlib.util.spec_from_file_location("converter", converter_path)
        converter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(converter)

        for program in range(128):
            pc_mod, pc_adsr, pc_waveform = get_instrument_params(program)
            conv_mod, conv_adsr, conv_waveform = converter.get_instrument_params(
                program
            )

            assert (
                pc_mod == conv_mod
            ), f"program {program}: mod mismatch {pc_mod} vs {conv_mod}"
            assert (
                int(pc_adsr) == conv_adsr
            ), f"program {program}: adsr mismatch {pc_adsr} vs {conv_adsr}"
            assert (
                int(pc_waveform) == conv_waveform
            ), f"program {program}: waveform mismatch {pc_waveform} vs {conv_waveform}"


class TestPercussionMapping:
    """Tests for percussion ADSR mapping."""

    def test_returns_valid_preset(self):
        from player.instruments import get_percussion_adsr

        for note in range(27, 88):
            adsr = get_percussion_adsr(note)
            assert (
                adsr in AdsrPreset.__members__.values()
            ), f"note {note}: invalid adsr {adsr}"

    def test_all_percussion_uses_percussion_preset(self):
        from player.instruments import get_percussion_adsr

        for note in range(27, 88):
            assert get_percussion_adsr(note) == AdsrPreset.PERCUSSION

    def test_percussion_preset_is_short(self):
        """PERCUSSION preset should have very fast decay and no sustain."""
        from player.envelope import ADSR_PRESETS

        a, d, s, r = ADSR_PRESETS[AdsrPreset.PERCUSSION]
        assert a <= 2, "attack should be near-instant"
        assert d <= 100, "decay should be fast"
        assert s == 0, "sustain should be zero"
        assert r <= 40, "release should be very short"
        # Total envelope < 50ms
        total_ms = (a + d + r) * 0.5
        assert total_ms <= 50

    def test_converter_percussion_consistency(self):
        """Verify player and converter percussion mappings match."""
        from player.instruments import get_percussion_adsr
        import importlib.util
        import os

        converter_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "midi_to_header.py",
        )
        spec = importlib.util.spec_from_file_location("converter", converter_path)
        converter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(converter)

        for note in range(27, 88):
            pc_adsr = int(get_percussion_adsr(note))
            conv_adsr = converter.get_percussion_adsr(note)
            assert (
                pc_adsr == conv_adsr
            ), f"note {note}: adsr mismatch {pc_adsr} vs {conv_adsr}"


class TestChannelConfig:
    """Tests for adaptive channel configuration."""

    def test_noise_ch_derived_from_num_channels(self):
        """Static NOISE_CH matches static NUM_CHANNELS (for C converter compat)."""
        from player.instruments import NOISE_CH
        from player.mixer import NUM_CHANNELS

        assert NOISE_CH == NUM_CHANNELS - 1

    def test_converter_noise_ch_matches(self):
        """Converter NOISE_CH must match player NOISE_CH."""
        from player.instruments import NOISE_CH
        import importlib.util
        import os

        converter_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "midi_to_header.py",
        )
        spec = importlib.util.spec_from_file_location("converter", converter_path)
        converter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(converter)

        assert NOISE_CH == converter.NOISE_CH

    def test_converter_num_channels_matches(self):
        from player.mixer import NUM_CHANNELS
        import importlib.util
        import os

        converter_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "midi_to_header.py",
        )
        spec = importlib.util.spec_from_file_location("converter", converter_path)
        converter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(converter)

        assert NUM_CHANNELS == converter.NUM_CHANNELS

    def test_sequencer_default_melodic_count(self):
        """Default Sequencer uses NUM_MELODIC oscillators."""
        from player.sequencer import Sequencer, NUM_MELODIC
        from player.mixer import NUM_CHANNELS

        seq = Sequencer()
        assert seq.num_melodic == NUM_MELODIC
        assert seq.num_channels == NUM_CHANNELS
        assert len(seq.oscillators) == NUM_MELODIC
        assert len(seq.envelopes) == NUM_CHANNELS

    def test_sequencer_adaptive_resize(self):
        """Sequencer resizes to match MIDI file's actual track count."""
        from player.sequencer import Sequencer, NoteEvent
        from player.envelope import AdsrPreset
        from player.oscillator import Waveform

        # Create 5 single-event tracks
        tracks = []
        for i in range(5):
            tracks.append(
                [
                    NoteEvent(
                        i * 100, 50, 1072, 80, i, 127, AdsrPreset.ORGAN, Waveform.SQUARE
                    )
                ]
            )

        seq = Sequencer()
        seq._resize(5)
        seq.load(tracks)
        assert seq.num_melodic == 5
        assert seq.num_channels == 6  # 5 melodic + 1 noise
        assert len(seq.oscillators) == 5
        assert len(seq.envelopes) == 6

    def test_sequencer_unlimited_channels(self):
        """Python sequencer has no upper limit on melodic channels."""
        from player.sequencer import Sequencer

        seq = Sequencer(num_melodic=20)
        assert seq.num_melodic == 20
        assert len(seq.oscillators) == 20
        assert len(seq.envelopes) == 21

    def test_load_midi_adapts_channels(self):
        """load_midi should set channel count from MIDI file."""
        import os
        from player.sequencer import Sequencer

        # Pirates has 2 melodic tracks, no percussion
        midi_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "resources",
            "Pirates of the Caribbean - He's a Pirate.mid",
        )
        if not os.path.exists(midi_path):
            return

        seq = Sequencer()
        seq.load_midi(midi_path)
        assert seq.num_melodic == 2
        assert len(seq.oscillators) == 2
