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

# Duty cycle values (only meaningful for WAVE_SQUARE)
MOD_50 = 127   # 50% - classic square wave
MOD_25 = 64    # 25% - brighter, thinner
MOD_12 = 32    # 12.5% - very thin, nasal


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
    if program < 8:       # Piano
        return (MOD_50, ADSR_PIANO, WAVE_TRIANGLE)
    elif program < 16:    # Chromatic Percussion
        return (MOD_25, ADSR_PIANO, WAVE_SQUARE)
    elif program < 24:    # Organ
        return (MOD_50, ADSR_ORGAN, WAVE_SQUARE)
    elif program < 32:    # Guitar
        return (MOD_50, ADSR_PIANO, WAVE_SAWTOOTH)
    elif program < 40:    # Bass
        return (MOD_50, ADSR_BASS, WAVE_SQUARE)
    elif program < 48:    # Strings
        return (MOD_50, ADSR_STRINGS, WAVE_SAWTOOTH)
    elif program < 56:    # Ensemble
        return (MOD_50, ADSR_STRINGS, WAVE_SAWTOOTH)
    elif program < 64:    # Brass
        return (MOD_50, ADSR_LEAD, WAVE_SAWTOOTH)
    elif program < 72:    # Reed
        return (MOD_25, ADSR_LEAD, WAVE_SQUARE)
    elif program < 80:    # Pipe
        return (MOD_50, ADSR_ORGAN, WAVE_TRIANGLE)
    elif program < 88:    # Synth Lead
        return (MOD_25, ADSR_LEAD, WAVE_PULSE_25)
    elif program < 96:    # Synth Pad
        return (MOD_50, ADSR_PAD, WAVE_TRIANGLE)
    elif program < 104:   # Synth Effects
        return (MOD_12, ADSR_DEFAULT, WAVE_SQUARE)
    elif program < 112:   # Ethnic
        return (MOD_50, ADSR_DEFAULT, WAVE_SAWTOOTH)
    elif program < 120:   # Percussive
        return (MOD_50, ADSR_PIANO, WAVE_SQUARE)
    else:                 # Sound Effects
        return (MOD_50, ADSR_DEFAULT, WAVE_SQUARE)


def midi_note_to_phase_inc(note):
    """Convert MIDI note number to phase increment for 16kHz sample rate."""
    if note < 24 or note > 108:
        return 0
    freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
    return round(freq * 65536 / SAMPLE_RATE)


def parse_midi(filename, max_tracks):
    mid = mido.MidiFile(filename)
    tracks = []

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

            if msg.type == 'set_tempo':
                tempo = msg.tempo
                continue

            if msg.type == 'program_change':
                current_program = msg.program
                continue

            if msg.type == 'note_on' and msg.velocity > 0:
                note_on_times[msg.note] = (current_time, current_program)
                note_on_velocities[msg.note] = msg.velocity
                continue

            if msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in note_on_times:
                    start_time, program = note_on_times[msg.note]
                    duration_ms = int((current_time - start_time) * 1000)
                    start_ms = int(start_time * 1000)
                    phase_inc = midi_note_to_phase_inc(msg.note)
                    volume = min(note_on_velocities[msg.note], 127)
                    mod, adsr, waveform = get_instrument_params(program)

                    if phase_inc > 0 and duration_ms > 0:
                        events.append((start_ms, phase_inc, duration_ms, volume, mod, adsr, waveform))

                    del note_on_times[msg.note]
                    del note_on_velocities[msg.note]

        if events:
            events.sort(key=lambda e: e[0])
            tracks.append(events)

    if len(tracks) > max_tracks:
        tracks.sort(key=lambda t: len(t), reverse=True)
        tracks = tracks[:max_tracks]

    return tracks


def assign_channels(tracks):
    """Assign oscillator channels to note events."""
    max_ch = 3

    for track_idx, events in enumerate(tracks):
        base_ch = track_idx % (max_ch + 1)
        active = {}

        for i, (start_ms, phase_inc, duration_ms, volume, mod, adsr, waveform) in enumerate(events):
            assigned_ch = base_ch
            expired = [ch for ch, off in active.items() if off <= start_ms]
            for ch in expired:
                del active[ch]

            if base_ch in active:
                for ch in range(max_ch + 1):
                    if ch not in active:
                        assigned_ch = ch
                        break
                else:
                    assigned_ch = base_ch

            active[assigned_ch] = start_ms + duration_ms
            events[i] = (start_ms, phase_inc, duration_ms, volume, assigned_ch, mod, adsr, waveform)


def generate_header(tracks, output_file, score_name):
    with open(output_file, 'w') as f:
        f.write("/*\n")
        f.write(f" * Auto-generated by midi_to_header.py\n")
        f.write(f" * Score: {score_name}\n")
        f.write(" */\n")
        f.write("#ifndef MIDI_DATA_H\n")
        f.write("#define MIDI_DATA_H\n\n")
        f.write("#include \"mp_sequencer.h\"\n\n")

        total_events = 0

        for i, events in enumerate(tracks):
            f.write(f"static const mp_note_event_t {score_name}_track{i}[] = {{\n")
            for (start_ms, phase_inc, duration_ms, volume, channel, mod, adsr, waveform) in events:
                f.write(f"    {{ .start_time_ms = {start_ms}, "
                        f".phase_inc = {phase_inc}, "
                        f".duration_ms = {duration_ms}, "
                        f".volume = {volume}, "
                        f".channel = {channel}, "
                        f".mod = {mod}, "
                        f".adsr_preset = {adsr}, "
                        f".waveform = {waveform} }},\n")
                total_events += 1
            f.write("};\n\n")

        f.write(f"static const mp_track_t {score_name}_tracks[] = {{\n")
        for i, events in enumerate(tracks):
            f.write(f"    {{ .events = {score_name}_track{i}, "
                    f".event_count = sizeof({score_name}_track{i}) "
                    f"/ sizeof({score_name}_track{i}[0]) }},\n")
        f.write("};\n\n")

        f.write(f"static const mp_score_t {score_name} = {{\n")
        f.write(f"    .tracks = {score_name}_tracks,\n")
        f.write(f"    .track_count = sizeof({score_name}_tracks) "
                f"/ sizeof({score_name}_tracks[0]),\n")
        f.write("};\n\n")
        f.write("#endif /* MIDI_DATA_H */\n")

        size_kb = total_events * 12 / 1024
        print(f"Generated: {output_file}")
        print(f"  Tracks: {len(tracks)}")
        print(f"  Total events: {total_events}")
        print(f"  Estimated Flash: {size_kb:.1f} KB")


def main():
    parser = argparse.ArgumentParser(description="Convert MIDI to MidiPlayer C header")
    parser.add_argument('input', help='Input MIDI file')
    parser.add_argument('output', help='Output .h file')
    parser.add_argument('--max-tracks', type=int, default=3, help='Max tracks (default: 3)')
    parser.add_argument('--name', default='midi_score', help='Score variable name')
    args = parser.parse_args()

    tracks = parse_midi(args.input, args.max_tracks)
    if not tracks:
        print("Error: No note events found in MIDI file", file=sys.stderr)
        sys.exit(1)

    assign_channels(tracks)
    generate_header(tracks, args.output, args.name)


if __name__ == '__main__':
    main()
