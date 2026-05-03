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
