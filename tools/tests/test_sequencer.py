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


def make_percussion_events():
    """Create percussion events assigned to noise channel."""
    from player.instruments import NOISE_CH

    return [
        NoteEvent(
            start_ms=0,
            duration_ms=50,
            phase_inc=0,  # noise has no phase_inc
            volume=100,
            channel=NOISE_CH,
            mod=0,
            adsr=AdsrPreset.LEAD,
            waveform=0,
        ),
        NoteEvent(
            start_ms=100,
            duration_ms=50,
            phase_inc=0,
            volume=80,
            channel=NOISE_CH,
            mod=0,
            adsr=AdsrPreset.PIANO,
            waveform=0,
        ),
    ]


class TestPercussionPlayback:
    def test_noise_channel_triggered(self):
        """Percussion events should trigger the noise channel envelope."""
        from player.instruments import NOISE_CH

        seq = Sequencer()
        seq.load([make_percussion_events()])

        seq.generate_chunk(256, 0)
        for ms in range(1, 10):
            seq.generate_chunk(256, ms)

        noise_env = seq.envelopes[NOISE_CH]
        assert noise_env.level > 0

    def test_noise_with_melodic(self):
        """Percussion and melodic tracks should play simultaneously."""
        from player.instruments import NOISE_CH

        seq = Sequencer()
        melodic = make_events()
        percussion = make_percussion_events()
        seq.load([melodic, percussion])

        seq.generate_chunk(256, 0)
        for ms in range(1, 10):
            seq.generate_chunk(256, ms)

        assert seq.oscillators[0].vol > 0
        assert seq.envelopes[NOISE_CH].level > 0

    def test_percussion_auto_stop(self):
        """Sequencer should stop after all percussion events finish."""
        seq = Sequencer()
        seq.load([make_percussion_events()])

        for ms in range(0, 500, 16):
            seq.generate_chunk(256, ms)

        assert not seq.playing

    def test_percussion_total_duration(self):
        """Total duration should include percussion events."""
        seq = Sequencer()
        perc = make_percussion_events()
        seq.load([perc])
        # Last event: start=100 + dur=50 = 150ms
        assert seq.total_ms == 150

    def test_parse_midi_includes_percussion(self):
        """parse_midi should include a percussion track for files with ch9."""
        import os

        midi_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "resources",
            "BeatIt.mid",
        )
        if not os.path.exists(midi_path):
            return  # skip if resource not available

        from player.sequencer import parse_midi

        tracks, num_channels, num_melodic = parse_midi(midi_path, max_tracks=0)

        # Last track should be percussion (all events on noise channel)
        perc_track = tracks[-1]
        noise_ch = num_melodic  # noise is right after melodic channels
        assert len(perc_track) > 0
        assert all(ev.channel == noise_ch for ev in perc_track)
        assert all(ev.phase_inc == 0 for ev in perc_track)

    def test_parse_midi_no_percussion(self):
        """parse_midi should work fine for files without percussion."""
        import os

        midi_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "resources",
            "Pirates of the Caribbean - He's a Pirate.mid",
        )
        if not os.path.exists(midi_path):
            return

        from player.sequencer import parse_midi

        tracks, num_channels, num_melodic = parse_midi(midi_path, max_tracks=0)

        # No track should have noise channel events
        noise_ch = num_melodic
        for trk in tracks:
            for ev in trk:
                assert ev.channel != noise_ch


class TestPauseResume:
    def test_pause_sets_flag(self):
        seq = Sequencer()
        seq.load([make_events()])
        assert not seq.paused
        seq.pause()
        assert seq.paused
        assert seq.playing  # still playing, just paused

    def test_resume_clears_flag(self):
        seq = Sequencer()
        seq.load([make_events()])
        seq.pause()
        seq.resume()
        assert not seq.paused

    def test_toggle_pause(self):
        seq = Sequencer()
        seq.load([make_events()])
        seq.toggle_pause()
        assert seq.paused
        seq.toggle_pause()
        assert not seq.paused

    def test_pause_when_not_playing_noop(self):
        seq = Sequencer()
        seq.pause()
        assert not seq.paused

    def test_resume_when_not_paused_noop(self):
        seq = Sequencer()
        seq.load([make_events()])
        seq.resume()  # not paused, should be noop
        assert not seq.paused


class TestSeek:
    def test_seek_to_beginning(self):
        seq = Sequencer()
        seq.load([make_events()])
        # Play a bit
        for ms in range(0, 150, 16):
            seq.generate_chunk(256, ms)
        assert seq.elapsed_ms > 0

        seq.seek(0)
        assert seq.elapsed_ms == 0
        assert seq.playing

    def test_seek_to_middle(self):
        seq = Sequencer()
        seq.load([make_events()])
        seq.seek(150)
        assert seq.elapsed_ms == 150

        # After seek, generating should pick up from 150ms
        # The second note starts at 200ms, so oscillator should be silent at 150
        seq.generate_chunk(256, 1000)  # wall-clock doesn't matter, elapsed anchored
        # elapsed should be around 150 (anchored by seek)

    def test_seek_past_end_clamps(self):
        seq = Sequencer()
        seq.load([make_events()])
        seq.seek(99999)
        assert seq.elapsed_ms == seq.total_ms

    def test_seek_negative_clamps(self):
        seq = Sequencer()
        seq.load([make_events()])
        seq.seek(-100)
        assert seq.elapsed_ms == 0

    def test_seek_resets_channels(self):
        seq = Sequencer()
        seq.load([make_events()])
        # Play first note
        for ms in range(0, 10):
            seq.generate_chunk(256, ms)
        assert seq.oscillators[0].vol > 0

        # Seek to after all notes
        seq.seek(250)
        # Channels should be silenced
        assert seq.oscillators[0].phase_inc == 0
        assert seq.oscillators[0].vol == 0

    def test_seek_then_play_continues(self):
        seq = Sequencer()
        seq.load([make_events()])
        seq.seek(0)

        # Should be able to play through normally after seek
        for ms in range(0, 600, 16):
            seq.generate_chunk(256, ms)
        assert not seq.playing

    def test_seek_empty_tracks_noop(self):
        seq = Sequencer()
        seq.seek(100)  # no tracks loaded, should not crash

    def test_seek_binary_search_accuracy(self):
        """Seek should position track index correctly via binary search."""
        events = [
            NoteEvent(0, 50, 1072, 80, 0, 127, AdsrPreset.ORGAN, Waveform.SQUARE),
            NoteEvent(100, 50, 1072, 80, 0, 127, AdsrPreset.ORGAN, Waveform.SQUARE),
            NoteEvent(200, 50, 1802, 60, 0, 127, AdsrPreset.ORGAN, Waveform.SQUARE),
            NoteEvent(300, 50, 1802, 60, 0, 127, AdsrPreset.ORGAN, Waveform.SQUARE),
        ]
        seq = Sequencer()
        seq.load([events])

        # Seek to 150ms — events at 0ms and 100ms are < 150, index = 2
        seq.seek(150)
        assert seq.track_indices[0] == 2

        # Seek to 100ms — only event at 0ms is < 100, index = 1
        # Event at 100ms will be replayed by _process_events
        seq.seek(100)
        assert seq.track_indices[0] == 1

        # Seek to 0ms — no events < 0, index = 0 (replay from start)
        seq.seek(0)
        assert seq.track_indices[0] == 0


class TestSpeed:
    def test_default_speed(self):
        seq = Sequencer()
        assert seq.speed == 1.0

    def test_set_speed(self):
        seq = Sequencer()
        seq.speed = 2.0
        assert seq.speed == 2.0

    def test_load_resets_speed(self):
        seq = Sequencer()
        seq.speed = 2.0
        seq.load([make_events()])
        assert seq.speed == 1.0


class TestFormat0MultiChannel:
    """Tests for Format 0 MIDI files with multiple channels in one track."""

    def test_format0_splits_by_midi_channel(self):
        """Format 0 files should produce one melodic track per MIDI channel."""
        import os

        # Baby.mid is Format 0 with ~10 MIDI channels in one track
        midi_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "resources",
            "Baby.mid",
        )
        if not os.path.exists(midi_path):
            return

        from player.sequencer import Sequencer

        seq = Sequencer()
        seq.load_midi(midi_path)
        # Baby has ~10 MIDI channels, should have more than 1 melodic
        assert (
            seq.num_melodic > 1
        ), f"Format 0 file should have multiple melodic channels, got {seq.num_melodic}"

    def test_format1_still_works(self):
        """Format 1 files should still work correctly."""
        import os

        # Pirates is Format 1 with 2 melodic tracks
        midi_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "resources",
            "Pirates of the Caribbean - He's a Pirate.mid",
        )
        if not os.path.exists(midi_path):
            return

        from player.sequencer import Sequencer

        seq = Sequencer()
        seq.load_midi(midi_path)
        assert seq.num_melodic == 2

    def test_all_midi_files_have_multiple_channels(self):
        """All MIDI files with multiple MIDI channels should get multiple tracks."""
        import os
        import mido

        resources = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "resources",
        )
        if not os.path.isdir(resources):
            return

        from player.sequencer import Sequencer

        for fname in sorted(os.listdir(resources)):
            if not fname.endswith(".mid"):
                continue
            path = os.path.join(resources, fname)
            mid = mido.MidiFile(path)

            # Count unique melodic MIDI channels
            melodic_chs = set()
            for track in mid.tracks:
                for msg in track:
                    if hasattr(msg, "channel") and msg.channel != 9:
                        if msg.type == "note_on" and msg.velocity > 0:
                            melodic_chs.add(msg.channel)

            if len(melodic_chs) <= 1:
                continue

            seq = Sequencer()
            seq.load_midi(path)
            assert seq.num_melodic >= 2, (
                f"{fname}: has {len(melodic_chs)} MIDI channels "
                f"but only {seq.num_melodic} melodic tracks"
            )


class TestPercussionRawVelocity:
    """Verify percussion uses raw MIDI velocity without scaling."""

    def test_player_percussion_raw_velocity(self):
        """parse_midi should not scale percussion velocity."""
        import os

        midi_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "resources",
            "BeatIt.mid",
        )
        if not os.path.exists(midi_path):
            return

        from player.sequencer import parse_midi

        tracks, _, num_melodic = parse_midi(midi_path, max_tracks=0)
        perc_track = tracks[-1]

        # All percussion velocities should be <= 127 (raw MIDI range)
        # and some should be > 50 (would be < 50 if scaled to 40%)
        vols = [ev.volume for ev in perc_track]
        assert max(vols) > 50, "Percussion velocity looks scaled down"
        assert all(0 < v <= 127 for v in vols)

    def test_converter_percussion_raw_velocity(self):
        """midi_to_header.py should not scale percussion velocity."""
        import os
        import importlib.util

        midi_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "resources",
            "BeatIt.mid",
        )
        if not os.path.exists(midi_path):
            return

        converter_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "midi_to_header.py",
        )
        spec = importlib.util.spec_from_file_location("converter", converter_path)
        converter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(converter)

        tracks = converter.parse_midi(midi_path, 0)
        # Last track is percussion (phase_inc == 0)
        perc_track = [t for t in tracks if all(e[1] == 0 for e in t)]
        assert perc_track, "No percussion track found"

        vols = [e[3] for e in perc_track[0]]  # index 3 = volume
        assert max(vols) > 50, "Converter percussion velocity looks scaled down"
        assert all(0 < v <= 127 for v in vols)
