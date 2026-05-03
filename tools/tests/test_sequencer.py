"""Tests for player.sequencer — event-driven note scheduling."""

from player.sequencer import Sequencer, NoteEvent
from player.oscillator import Waveform
from player.envelope import AdsrPreset


def make_events():
    """Create simple test events."""
    return [
        NoteEvent(
            start_ms=0,
            duration_ms=100,
            phase_inc=1072,
            volume=80,
            channel=0,
            mod=127,
            adsr=AdsrPreset.ORGAN,
            waveform=Waveform.SQUARE,
        ),
        NoteEvent(
            start_ms=200,
            duration_ms=100,
            phase_inc=1802,
            volume=60,
            channel=0,
            mod=127,
            adsr=AdsrPreset.ORGAN,
            waveform=Waveform.SQUARE,
        ),
    ]


class TestSequencer:
    def test_init_not_playing(self):
        seq = Sequencer()
        assert not seq.playing

    def test_load_starts_playing(self):
        seq = Sequencer()
        seq.load([make_events()])
        assert seq.playing

    def test_total_duration(self):
        seq = Sequencer()
        seq.load([make_events()])
        # Last event: start=200 + dur=100 = 300ms
        assert seq.total_ms == 300

    def test_progress(self):
        seq = Sequencer()
        seq.load([make_events()])

        # Generate at 150ms -> ~50%
        seq.generate_chunk(256, 1)
        seq.generate_chunk(256, 150)
        pct = seq.progress_pct
        assert 40 <= pct <= 60

    def test_auto_stop(self):
        seq = Sequencer()
        seq.load([make_events()])

        # Run past all events + release
        for ms in range(0, 600, 16):
            seq.generate_chunk(256, ms)

        assert not seq.playing

    def test_generate_chunk_returns_valid(self):
        seq = Sequencer()
        seq.load([make_events()])
        chunk = seq.generate_chunk(256, 0)
        assert len(chunk) == 256
        assert chunk.min() >= 0
        assert chunk.max() <= 1023

    def test_note_triggers_oscillator(self):
        seq = Sequencer()
        seq.load([make_events()])

        # After first event, oscillator should have freq set
        seq.generate_chunk(256, 0)
        # Run a few ticks for envelope to ramp up
        for ms in range(1, 10):
            seq.generate_chunk(256, ms)

        assert seq.oscillators[0].phase_inc == 1072
        assert seq.oscillators[0].vol > 0

    def test_max_duration_cap(self):
        ev = NoteEvent(0, 99999, 1072, 80, 0, 127, 0, 0)
        assert ev.duration_ms == 4095
