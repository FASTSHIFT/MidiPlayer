"""
GM Instrument mapping — shared with tools/midi_to_header.py.

Maps MIDI program numbers to (mod, adsr_preset, waveform).
"""

from .oscillator import Waveform
from .envelope import AdsrPreset

# Duty cycle values
MOD_50 = 127
MOD_25 = 64
MOD_12 = 32


def get_instrument_params(program):
    """
    Map MIDI program number to (mod, adsr_preset, waveform).

    Returns:
        tuple: (mod: int, adsr: AdsrPreset, waveform: Waveform)
    """
    if program < 8:  # Piano
        return (MOD_50, AdsrPreset.PIANO, Waveform.TRIANGLE)
    elif program < 16:  # Chromatic Percussion
        return (MOD_25, AdsrPreset.PIANO, Waveform.SQUARE)
    elif program < 24:  # Organ
        return (MOD_50, AdsrPreset.ORGAN, Waveform.SQUARE)
    elif program < 32:  # Guitar
        return (MOD_50, AdsrPreset.PIANO, Waveform.SAWTOOTH)
    elif program < 40:  # Bass
        return (MOD_50, AdsrPreset.BASS, Waveform.SQUARE)
    elif program < 48:  # Strings
        return (MOD_50, AdsrPreset.STRINGS, Waveform.SAWTOOTH)
    elif program < 56:  # Ensemble
        return (MOD_50, AdsrPreset.STRINGS, Waveform.SAWTOOTH)
    elif program < 64:  # Brass
        return (MOD_50, AdsrPreset.LEAD, Waveform.SAWTOOTH)
    elif program < 72:  # Reed
        return (MOD_25, AdsrPreset.LEAD, Waveform.SQUARE)
    elif program < 80:  # Pipe
        return (MOD_50, AdsrPreset.ORGAN, Waveform.TRIANGLE)
    elif program < 88:  # Synth Lead
        return (MOD_25, AdsrPreset.LEAD, Waveform.PULSE_25)
    elif program < 96:  # Synth Pad
        return (MOD_50, AdsrPreset.PAD, Waveform.TRIANGLE)
    elif program < 104:  # Synth Effects
        return (MOD_12, AdsrPreset.DEFAULT, Waveform.SQUARE)
    elif program < 112:  # Ethnic
        return (MOD_50, AdsrPreset.DEFAULT, Waveform.SAWTOOTH)
    elif program < 120:  # Percussive
        return (MOD_50, AdsrPreset.PIANO, Waveform.SQUARE)
    else:  # Sound Effects
        return (MOD_50, AdsrPreset.DEFAULT, Waveform.SQUARE)
