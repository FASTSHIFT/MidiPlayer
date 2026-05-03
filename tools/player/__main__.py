"""
MidiPlayer PC — CLI entry point.

Usage:
    python -m player song.mid
    python -m player song.mid -t 5
    python -m player song.mid -o output.wav
    python -m player song.mid --vis
"""

import argparse
import time
import threading
import numpy as np

from .sequencer import Sequencer
from .mixer import Mixer
from .oscillator import SAMPLE_RATE

CHUNK_SIZE = 256  # 16ms at 16kHz
AUDIO_BUFFER_CHUNKS = 4  # pyaudio buffer = 4 chunks = 64ms headroom


def play_audio(seq, mute=False, visualizer=None):
    """Play audio through pyaudio, optionally feeding visualizer."""
    stream = None
    pa = None

    wall_start = time.time()
    last_wall = wall_start
    last_print = 0

    # Wait for visualizer to be ready before starting the clock
    if visualizer:
        while not visualizer.running:
            time.sleep(0.01)

    # Init pyaudio AFTER visualizer is ready (avoids blocking vis startup)
    if not mute:
        import pyaudio

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE * AUDIO_BUFFER_CHUNKS,
        )

    # Reset wall clock after ALL init is done (pyaudio + visualizer)
    chunk_ms = CHUNK_SIZE * 1000 // SAMPLE_RATE  # 16ms per chunk
    seq_time_ms = 0  # sequencer time, advanced by chunk_ms each iteration
    last_print = 0

    # Pre-buffer: generate a few chunks to fill pyaudio's buffer before playback
    if stream:
        for _ in range(AUDIO_BUFFER_CHUNKS):
            seq_time_ms += chunk_ms
            samples = seq.generate_chunk(CHUNK_SIZE, seq_time_ms)
            audio = Mixer.to_float32(samples)
            stream.write(audio.tobytes())

    wall_start = time.time()
    last_wall = wall_start

    try:
        while seq.playing:
            if visualizer and not visualizer.running:
                break

            now = time.time()

            if seq.paused:
                # While paused, keep adjusting wall_start so time doesn't jump
                wall_start += now - last_wall
                last_wall = now
                if stream:
                    silence = np.zeros(CHUNK_SIZE, dtype=np.float32)
                    stream.write(silence.tobytes())
                else:
                    time.sleep(CHUNK_SIZE / SAMPLE_RATE)
                continue

            last_wall = now

            # Sync with sequencer after seek
            if abs(seq.elapsed_ms - seq_time_ms) > chunk_ms * 2:
                seq_time_ms = seq.elapsed_ms

            # Advance sequencer time by one chunk worth of ms, scaled by speed
            seq_time_ms += int(chunk_ms * seq.speed)
            current_ms = seq_time_ms

            # Generate per-channel samples for visualizer
            if visualizer:
                seq._process_events(current_ms)
                ticks = CHUNK_SIZE // 8
                for _ in range(max(1, ticks) - 1):
                    for ch in range(seq.num_channels):
                        level = seq.envelopes[ch].tick()
                        if ch < seq.num_melodic:
                            seq.oscillators[ch].set_vol(level)
                        else:
                            seq.noise.set_vol(level)

                ch_samples = []
                for osc in seq.oscillators:
                    ch_samples.append(osc.generate(CHUNK_SIZE))
                ch_samples.append(seq.noise.generate(CHUNK_SIZE))
                mix = seq.mixer.mix(ch_samples)
                visualizer.update_buffers(ch_samples, mix)
                audio = Mixer.to_float32(mix)
            else:
                samples = seq.generate_chunk(CHUNK_SIZE, current_ms)
                audio = Mixer.to_float32(samples)

            if stream:
                stream.write(audio.tobytes())
            else:
                time.sleep(CHUNK_SIZE / SAMPLE_RATE)

            # Print progress (non-vis mode only)
            if now - last_print >= 1.0 and not visualizer:
                last_print = now
                pct = seq.progress_pct
                elapsed = seq.elapsed_ms
                total = seq.total_ms
                e_min, e_sec = elapsed // 60000, (elapsed % 60000) // 1000
                t_min, t_sec = total // 60000, (total % 60000) // 1000
                spd = f" {seq.speed:.1f}×" if seq.speed != 1.0 else ""
                print(
                    f"\r[{pct:3d}%] {e_min}:{e_sec:02d} / " f"{t_min}:{t_sec:02d}{spd}",
                    end="",
                    flush=True,
                )

    except KeyboardInterrupt:
        pass
    finally:
        if not visualizer:
            print()
        if stream:
            stream.stop_stream()
            stream.close()
            pa.terminate()


def export_wav(seq, output_path):
    """Render to WAV file (offline, no pyaudio needed)."""
    import wave

    print(f"Rendering to {output_path}...")

    frames = []
    current_ms = 1
    chunk_ms = CHUNK_SIZE * 1000 // SAMPLE_RATE

    while seq.playing:
        samples = seq.generate_chunk(CHUNK_SIZE, current_ms)
        audio = Mixer.to_float32(samples)
        pcm = (audio * 32767).astype(np.int16)
        frames.append(pcm.tobytes())
        current_ms += chunk_ms

    with wave.open(output_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))

    duration_s = current_ms / 1000
    print(f"Done: {duration_s:.1f}s, {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="MidiPlayer PC — MCU-identical MIDI synthesizer"
    )
    parser.add_argument("input", help="MIDI file to play")
    parser.add_argument(
        "-t",
        "--tracks",
        type=int,
        default=0,
        help="Max tracks (0 = all, default: all)",
    )
    parser.add_argument("-o", "--output", help="Export to WAV file")
    parser.add_argument("--mute", action="store_true", help="Mute audio output")
    parser.add_argument(
        "--vis", action="store_true", help="Show real-time waveform visualization"
    )
    args = parser.parse_args()

    seq = Sequencer()
    num_tracks = seq.load_midi(args.input, args.tracks)
    print(f"Loaded: {args.input}")
    print(
        f"Tracks: {num_tracks}, Channels: {seq.num_melodic}+noise, "
        f"Duration: {seq.total_ms // 1000}s"
    )

    if args.output:
        export_wav(seq, args.output)
    elif args.vis:
        from .visualizer import Visualizer

        vis = Visualizer(seq)

        audio_thread = threading.Thread(
            target=play_audio, args=(seq, args.mute, vis), daemon=True
        )
        audio_thread.start()

        vis.run()
    else:
        play_audio(seq, mute=args.mute)


if __name__ == "__main__":
    main()
