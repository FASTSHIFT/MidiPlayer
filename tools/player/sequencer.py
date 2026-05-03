"""
Sequencer — MIDI event-driven note scheduler.

Port of source/mp_sequencer.c logic.
Parses MIDI files and drives oscillators + envelopes.
"""

import mido
from .oscillator import Oscillator, NoiseChannel, midi_note_to_phase_inc
from .envelope import Envelope
from .mixer import Mixer, NUM_CHANNELS
from .instruments import get_instrument_params

PRESCALER_DIV = 8  # Envelope tick every 8 samples (2kHz at 16kHz SR)
MAX_NOTE_DURATION_MS = 4095
NUM_MELODIC = NUM_CHANNELS - 1  # 3 melodic channels


class NoteEvent:
    """Pre-parsed note event."""

    __slots__ = [
        "start_ms",
        "duration_ms",
        "phase_inc",
        "volume",
        "channel",
        "mod",
        "adsr_preset",
        "waveform",
    ]

    def __init__(
        self, start_ms, duration_ms, phase_inc, volume, channel, mod, adsr, waveform
    ):
        self.start_ms = start_ms
        self.duration_ms = min(duration_ms, MAX_NOTE_DURATION_MS)
        self.phase_inc = phase_inc
        self.volume = volume
        self.channel = channel
        self.mod = mod
        self.adsr_preset = adsr
        self.waveform = waveform


def parse_midi(filename, max_tracks=3):
    """Parse MIDI file into list of NoteEvent lists (one per track)."""
    mid = mido.MidiFile(filename)
    tracks = []

    for track in mid.tracks:
        events = []
        current_time = 0.0
        tempo = 500000
        current_program = 0
        note_on_times = {}
        note_on_velocities = {}

        for msg in track:
            dt = mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
            current_time += dt

            if msg.type == "set_tempo":
                tempo = msg.tempo
                continue
            if msg.type == "program_change":
                current_program = msg.program
                continue
            # Skip percussion channel 9
            if hasattr(msg, "channel") and msg.channel == 9:
                continue

            if msg.type == "note_on" and msg.velocity > 0:
                note_on_times[msg.note] = (current_time, current_program)
                note_on_velocities[msg.note] = msg.velocity
            elif msg.type == "note_off" or (
                msg.type == "note_on" and msg.velocity == 0
            ):
                if msg.note in note_on_times:
                    start_time, program = note_on_times[msg.note]
                    dur_ms = int((current_time - start_time) * 1000)
                    start_ms = int(start_time * 1000)
                    phase_inc = midi_note_to_phase_inc(msg.note)
                    volume = min(note_on_velocities[msg.note], 127)
                    mod, adsr, waveform = get_instrument_params(program)

                    if phase_inc > 0 and dur_ms > 0:
                        events.append(
                            NoteEvent(
                                start_ms,
                                dur_ms,
                                phase_inc,
                                volume,
                                0,
                                mod,
                                adsr,
                                waveform,
                            )
                        )
                    del note_on_times[msg.note]
                    del note_on_velocities[msg.note]

        if events:
            events.sort(key=lambda e: e.start_ms)
            tracks.append(events)

    # Keep tracks with most notes (0 or negative = keep all)
    if max_tracks > 0 and len(tracks) > max_tracks:
        tracks.sort(key=len, reverse=True)
        tracks = tracks[:max_tracks]

    # Assign channels (0~2 melodic only)
    for track_idx, events in enumerate(tracks):
        base_ch = track_idx % NUM_MELODIC
        active = {}
        for ev in events:
            expired = [ch for ch, off in active.items() if off <= ev.start_ms]
            for ch in expired:
                del active[ch]

            assigned = base_ch
            if base_ch in active:
                for ch in range(NUM_MELODIC):
                    if ch not in active:
                        assigned = ch
                        break
            active[assigned] = ev.start_ms + ev.duration_ms
            ev.channel = assigned

    return tracks


class Sequencer:
    """Event-driven sequencer driving oscillators and envelopes."""

    def __init__(self):
        self.oscillators = [Oscillator() for _ in range(NUM_MELODIC)]
        self.noise = NoiseChannel()
        self.envelopes = [Envelope() for _ in range(NUM_CHANNELS)]
        self.mixer = Mixer()

        self.tracks = []
        self.track_indices = []
        self.channel_off_times = {}  # channel -> off_time_ms
        self.playing = False
        self.start_ms = 0
        self.elapsed_ms = 0
        self.total_ms = 0

    def load(self, tracks):
        """Load pre-parsed tracks."""
        self.tracks = tracks
        self.track_indices = [0] * len(tracks)
        self.channel_off_times = {}
        self.playing = True
        self.start_ms = 0
        self.elapsed_ms = 0

        # Compute total duration
        max_end = 0
        for trk in tracks:
            if trk:
                last = trk[-1]
                end = last.start_ms + last.duration_ms
                if end > max_end:
                    max_end = end
        self.total_ms = max_end

        # Reset all channels
        for osc in self.oscillators:
            osc.silence()
        self.noise.silence()
        for env in self.envelopes:
            env.__init__()

    def load_midi(self, filename, max_tracks=0):
        """Parse MIDI file and load tracks. max_tracks=0 means all."""
        tracks = parse_midi(filename, max_tracks)
        self.load(tracks)
        return len(tracks)

    def _process_events(self, current_ms):
        """Process note on/off events up to current_ms."""
        if self.start_ms == 0:
            self.start_ms = current_ms

        elapsed = current_ms - self.start_ms
        self.elapsed_ms = elapsed

        # Process note-offs for all channels
        for ch in list(self.channel_off_times.keys()):
            if elapsed >= self.channel_off_times[ch]:
                self.envelopes[ch].note_off()
                if ch < NUM_MELODIC:
                    self.oscillators[ch].set_freq(0)
                del self.channel_off_times[ch]

        # Process note-ons from all tracks
        all_done = True
        for t in range(len(self.tracks)):
            trk = self.tracks[t]

            while self.track_indices[t] < len(trk):
                ev = trk[self.track_indices[t]]
                if ev.start_ms > elapsed:
                    break

                ch = ev.channel
                if ch < NUM_MELODIC:
                    self.oscillators[ch].set_mod(ev.mod)
                    self.oscillators[ch].set_waveform(ev.waveform)
                    self.oscillators[ch].set_freq(ev.phase_inc)
                self.envelopes[ch].set_preset(ev.adsr_preset)
                self.envelopes[ch].note_on(ev.volume)

                self.channel_off_times[ch] = ev.start_ms + ev.duration_ms
                self.track_indices[t] += 1

            if self.track_indices[t] < len(trk):
                all_done = False

        if self.channel_off_times:
            all_done = False

        # Envelope tick
        for ch in range(NUM_CHANNELS):
            level = self.envelopes[ch].tick()
            if ch < NUM_MELODIC:
                self.oscillators[ch].set_vol(level)
            else:
                self.noise.set_vol(level)

        if all_done:
            env_active = any(e.level > 0 for e in self.envelopes)
            if not env_active:
                self.playing = False

    def generate_chunk(self, chunk_size, current_ms):
        """
        Generate a chunk of mixed audio samples.

        Args:
            chunk_size: number of samples to generate
            current_ms: current time in milliseconds

        Returns:
            numpy uint16 array (10-bit, 0~1023)
        """
        # Process events at start of chunk
        self._process_events(current_ms)

        # Run envelope ticks during chunk (every PRESCALER_DIV samples)
        # For simplicity, we tick once per chunk at 2kHz equivalent
        ticks_in_chunk = chunk_size // PRESCALER_DIV
        for _ in range(max(1, ticks_in_chunk) - 1):
            for ch in range(NUM_CHANNELS):
                level = self.envelopes[ch].tick()
                if ch < NUM_MELODIC:
                    self.oscillators[ch].set_vol(level)
                else:
                    self.noise.set_vol(level)

        # Generate samples from all channels
        ch_samples = []
        for osc in self.oscillators:
            ch_samples.append(osc.generate(chunk_size))
        ch_samples.append(self.noise.generate(chunk_size))

        return self.mixer.mix(ch_samples)

    @property
    def progress_pct(self):
        if self.total_ms == 0:
            return 0
        pct = self.elapsed_ms * 100 // self.total_ms
        return min(pct, 100)
