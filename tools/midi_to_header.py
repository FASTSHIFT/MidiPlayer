#!/usr/bin/env python3
"""
Convert a MIDI file to a C header for MidiPlayer library.

Outputs mp_note_event_t / mp_track_t / mp_score_t structures
compatible with source/mp_sequencer.h.

Supports waveform selection, ADSR envelope presets, and duty cycle
modulation based on MIDI program (instrument) numbers.

Usage:
    python3 midi_to_header.py input.mid output.h [--max-tracks N] [--name SCORE_NAME]
"""

import mido
import argparse
import sys

SAMPLE_RATE = 16000

# Waveform indices (must match mp_waveform_t in mp_osc.h)
WAVE_SQUARE = 0
WAVE_TRIANGLE = 1
WAVE_SAWTOOTH = 2
WAVE_PULSE_25 = 3

# ADSR preset indices (must match mp_adsr_preset_t in mp_envelope.h)
ADSR_DEFAULT = 0
ADSR_PIANO = 1
ADSR_ORGAN = 2
ADSR_STRINGS = 3
ADSR_BASS = 4
ADSR_LEAD = 5
ADSR_PAD = 6
ADSR_PERCUSSION = 7

# Duty cycle values (only meaningful for WAVE_SQUARE)
MOD_50 = 127  # 50% - classic square wave
MOD_25 = 64  # 25% - brighter, thinner
MOD_12 = 32  # 12.5% - very thin, nasal


def get_instrument_params(program):
    """Map MIDI program number to (mod, adsr_preset, waveform).

    General MIDI instrument families (0-indexed):
      0-7:   Piano           -> triangle + piano ADSR (soft percussive)
      8-15:  Chromatic Perc  -> square 25% + piano ADSR
      16-23: Organ           -> square 50% + organ ADSR (sustained)
      24-31: Guitar          -> sawtooth + piano ADSR (plucked)
      32-39: Bass            -> square 50% + bass ADSR
      40-47: Strings         -> sawtooth + strings ADSR (bowed)
      48-55: Ensemble        -> sawtooth + strings ADSR
      56-63: Brass           -> sawtooth + lead ADSR (bold)
      64-71: Reed            -> square 25% + lead ADSR
      72-79: Pipe            -> triangle + organ ADSR (flute-like)
      80-87: Synth Lead      -> pulse 25% + lead ADSR
      88-95: Synth Pad       -> triangle + pad ADSR (ambient)
      96-103: Synth Effects  -> square 12% + default ADSR
      104-111: Ethnic        -> sawtooth + default ADSR
      112-119: Percussive    -> square 50% + piano ADSR
      120-127: Sound Effects -> square 50% + default ADSR
    """
    if program < 8:  # Piano
        return (MOD_50, ADSR_PIANO, WAVE_TRIANGLE)
    elif program < 16:  # Chromatic Percussion
        return (MOD_25, ADSR_PIANO, WAVE_SQUARE)
    elif program < 24:  # Organ
        return (MOD_50, ADSR_ORGAN, WAVE_SQUARE)
    elif program < 32:  # Guitar
        return (MOD_50, ADSR_PIANO, WAVE_SAWTOOTH)
    elif program < 40:  # Bass
        return (MOD_50, ADSR_BASS, WAVE_SQUARE)
    elif program < 48:  # Strings
        return (MOD_50, ADSR_STRINGS, WAVE_SAWTOOTH)
    elif program < 56:  # Ensemble
        return (MOD_50, ADSR_STRINGS, WAVE_SAWTOOTH)
    elif program < 64:  # Brass
        return (MOD_50, ADSR_LEAD, WAVE_SAWTOOTH)
    elif program < 72:  # Reed
        return (MOD_25, ADSR_LEAD, WAVE_SQUARE)
    elif program < 80:  # Pipe
        return (MOD_50, ADSR_ORGAN, WAVE_TRIANGLE)
    elif program < 88:  # Synth Lead
        return (MOD_25, ADSR_LEAD, WAVE_PULSE_25)
    elif program < 96:  # Synth Pad
        return (MOD_50, ADSR_PAD, WAVE_TRIANGLE)
    elif program < 104:  # Synth Effects
        return (MOD_12, ADSR_DEFAULT, WAVE_SQUARE)
    elif program < 112:  # Ethnic
        return (MOD_50, ADSR_DEFAULT, WAVE_SAWTOOTH)
    elif program < 120:  # Percussive
        return (MOD_50, ADSR_PIANO, WAVE_SQUARE)
    else:  # Sound Effects
        return (MOD_50, ADSR_DEFAULT, WAVE_SQUARE)


def midi_note_to_phase_inc(note):
    """Convert MIDI note number to phase increment for 16kHz sample rate."""
    if note < 24 or note > 108:
        return 0
    freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
    return round(freq * 65536 / SAMPLE_RATE)


# Channel configuration (must match MP_OSC_CH_COUNT / MP_OSC_NOISE_CH)
NUM_CHANNELS = 8
NOISE_CH = NUM_CHANNELS - 1

# Maximum note duration in ms (12-bit field, max 4095)
MAX_NOTE_DURATION_MS = 4095


def get_percussion_adsr(note):
    """Map GM percussion note to ADSR preset index for the noise channel."""
    return ADSR_PERCUSSION


def parse_midi(filename, max_tracks):
    """Parse MIDI file into melodic tracks + one percussion track.

    Melodic events (non-ch9) are collected per-track.
    Percussion events (ch9) are merged into a single track for the noise channel.
    """
    mid = mido.MidiFile(filename)
    melodic_tracks = []
    percussion_events = []

    for track in mid.tracks:
        events = []
        current_time = 0.0
        tempo = 500000  # default 120 BPM
        current_program = 0
        note_on_times = {}
        note_on_velocities = {}

        for msg in track:
            delta_time = mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
            current_time += delta_time

            if msg.type == "set_tempo":
                tempo = msg.tempo
                continue

            if msg.type == "program_change":
                current_program = msg.program
                continue

            is_percussion = hasattr(msg, "channel") and msg.channel == 9

            if msg.type == "note_on" and msg.velocity > 0:
                note_on_times[msg.note] = (current_time, current_program)
                note_on_velocities[msg.note] = msg.velocity
                continue

            if msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                if msg.note in note_on_times:
                    start_time, program = note_on_times[msg.note]
                    duration_ms = int((current_time - start_time) * 1000)
                    start_ms = int(start_time * 1000)
                    volume = min(note_on_velocities[msg.note], 127)

                    if is_percussion:
                        adsr = get_percussion_adsr(msg.note)
                        if duration_ms > 0:
                            percussion_events.append(
                                (
                                    start_ms,
                                    0,  # phase_inc = 0 for noise
                                    duration_ms,
                                    volume,
                                    0,  # mod (unused for noise)
                                    adsr,
                                    0,  # waveform (unused for noise)
                                )
                            )
                    else:
                        phase_inc = midi_note_to_phase_inc(msg.note)
                        mod, adsr, waveform = get_instrument_params(program)

                        if duration_ms > MAX_NOTE_DURATION_MS:
                            duration_ms = MAX_NOTE_DURATION_MS

                        if phase_inc > 0 and duration_ms > 0:
                            events.append(
                                (
                                    start_ms,
                                    phase_inc,
                                    duration_ms,
                                    volume,
                                    mod,
                                    adsr,
                                    waveform,
                                )
                            )

                    del note_on_times[msg.note]
                    del note_on_velocities[msg.note]

        if events:
            events.sort(key=lambda e: e[0])
            melodic_tracks.append(events)

    if len(melodic_tracks) > max_tracks:
        melodic_tracks.sort(key=lambda t: len(t), reverse=True)
        melodic_tracks = melodic_tracks[:max_tracks]

    # Append percussion as a separate track (assigned to NOISE_CH in assign_channels)
    tracks = melodic_tracks
    if percussion_events:
        percussion_events.sort(key=lambda e: e[0])
        tracks.append(percussion_events)

    return tracks


def assign_channels(tracks):
    """Assign oscillator channels to note events.

    Melodic tracks use channels 0-2 via round-robin + spillover.
    Melodic tracks use channels 0-6 via round-robin + spillover.
    The last track may be percussion (phase_inc == 0), assigned to channel 7 (noise).
    """
    num_melodic_ch = NOISE_CH  # channels 0~6

    for track_idx, events in enumerate(tracks):
        # Detect percussion track: all events have phase_inc == 0
        is_percussion = all(e[1] == 0 for e in events)

        if is_percussion:
            # Assign all percussion events to noise channel
            for i, (
                start_ms,
                phase_inc,
                duration_ms,
                volume,
                mod,
                adsr,
                waveform,
            ) in enumerate(events):
                events[i] = (
                    start_ms,
                    phase_inc,
                    duration_ms,
                    volume,
                    NOISE_CH,
                    mod,
                    adsr,
                    waveform,
                )
            continue

        base_ch = track_idx % num_melodic_ch
        active = {}  # channel -> off_time

        for i, (
            start_ms,
            phase_inc,
            duration_ms,
            volume,
            mod,
            adsr,
            waveform,
        ) in enumerate(events):
            assigned_ch = base_ch
            # Release expired notes
            expired = [ch for ch, off in active.items() if off <= start_ms]
            for ch in expired:
                del active[ch]

            # If base channel is busy, try other melodic channels
            if base_ch in active:
                for ch in range(num_melodic_ch):
                    if ch not in active:
                        assigned_ch = ch
                        break
                else:
                    # All melodic channels busy, steal base channel
                    assigned_ch = base_ch

            active[assigned_ch] = start_ms + duration_ms
            events[i] = (
                start_ms,
                phase_inc,
                duration_ms,
                volume,
                assigned_ch,
                mod,
                adsr,
                waveform,
            )


# Mod value -> mod_idx mapping (must match mp_mod_table in mp_sequencer.h)
# 2-bit index: 0=50%, 1=25%, 2=12.5%, 3=75%
MOD_TO_IDX = {127: 0, 64: 1, 32: 2, 191: 3}


def mod_value_to_idx(mod):
    """Convert a mod value to its 2-bit index. Default to 0 (50%)."""
    return MOD_TO_IDX.get(mod, 0)


def pack_word0(start_ms, duration_ms):
    """Pack start_time_ms (20 bits) and duration_ms (12 bits) into uint32_t."""
    return (start_ms & 0xFFFFF) | ((duration_ms & 0xFFF) << 20)


def pack_word1(phase_inc, volume, channel, mod_idx, adsr, waveform):
    """Pack remaining fields into uint32_t (new 8-channel layout)."""
    return (
        (phase_inc & 0x7FFF)
        | ((volume & 0x7F) << 15)
        | ((channel & 0x07) << 22)
        | ((mod_idx & 0x03) << 25)
        | ((adsr & 0x07) << 27)
        | ((waveform & 0x03) << 30)
    )


def generate_header(tracks, output_file, score_name):
    with open(output_file, "w") as f:
        f.write("/*\n")
        f.write(" * Auto-generated by midi_to_header.py — DO NOT EDIT\n")
        f.write(f" * Score: {score_name}\n")
        f.write(" * Packed format: 8 bytes per event (2x uint32_t)\n")
        f.write(" */\n")
        f.write("/* clang-format off */\n")
        f.write("#ifndef MIDI_DATA_H\n")
        f.write("#define MIDI_DATA_H\n\n")
        f.write('#include "mp_sequencer.h"\n\n')

        total_events = 0

        for i, events in enumerate(tracks):
            f.write(f"static const mp_note_event_t {score_name}_track{i}[] = {{\n")
            for (
                start_ms,
                phase_inc,
                duration_ms,
                volume,
                channel,
                mod,
                adsr,
                waveform,
            ) in events:
                mod_idx = mod_value_to_idx(mod)
                w0 = pack_word0(start_ms, duration_ms)
                w1 = pack_word1(phase_inc, volume, channel, mod_idx, adsr, waveform)
                f.write(f"    {{ 0x{w0:08X}, 0x{w1:08X} }},\n")
                total_events += 1
            f.write("};\n\n")

        f.write(f"static const mp_track_t {score_name}_tracks[] = {{\n")
        for i, events in enumerate(tracks):
            f.write(
                f"    {{ .events = {score_name}_track{i}, "
                f".event_count = sizeof({score_name}_track{i}) "
                f"/ sizeof({score_name}_track{i}[0]) }},\n"
            )
        f.write("};\n\n")

        f.write(f"static const mp_score_t {score_name} = {{\n")
        f.write(f"    .tracks = {score_name}_tracks,\n")
        f.write(
            f"    .track_count = sizeof({score_name}_tracks) "
            f"/ sizeof({score_name}_tracks[0]),\n"
        )
        f.write("};\n\n")
        f.write("#endif /* MIDI_DATA_H */\n")
        f.write("/* clang-format on */\n")

        size_kb = total_events * 8 / 1024
        print(f"Generated: {output_file}")
        print(f"  Tracks: {len(tracks)}")
        print(f"  Total events: {total_events}")
        print(f"  Flash: {size_kb:.1f} KB ({total_events} x 8 bytes)")


def main():
    parser = argparse.ArgumentParser(description="Convert MIDI to MidiPlayer C header")
    parser.add_argument("input", help="Input MIDI file")
    parser.add_argument("output", help="Output .h file")
    parser.add_argument(
        "--max-tracks", type=int, default=3, help="Max tracks (default: 3)"
    )
    parser.add_argument("--name", default="midi_score", help="Score variable name")
    args = parser.parse_args()

    tracks = parse_midi(args.input, args.max_tracks)
    if not tracks:
        print("Error: No note events found in MIDI file", file=sys.stderr)
        sys.exit(1)

    assign_channels(tracks)
    generate_header(tracks, args.output, args.name)


if __name__ == "__main__":
    main()
