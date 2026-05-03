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
import numpy as np

from .sequencer import Sequencer
from .mixer import Mixer
from .oscillator import SAMPLE_RATE

CHUNK_SIZE = 256  # 16ms at 16kHz


def play_audio(seq, mute=False):
    """Play audio through pyaudio."""
    if not mute:
        import pyaudio

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE,
        )
    else:
        stream = None

    start_time = time.time()
    last_print = 0

    try:
        while seq.playing:
            elapsed_s = time.time() - start_time
            current_ms = int(elapsed_s * 1000)

            samples = seq.generate_chunk(CHUNK_SIZE, current_ms)
            audio = Mixer.to_float32(samples)

            if stream:
                stream.write(audio.tobytes())
            else:
                # Mute mode: throttle to ~realtime
                time.sleep(CHUNK_SIZE / SAMPLE_RATE)

            # Print progress every second
            now = time.time()
            if now - last_print >= 1.0:
                last_print = now
                pct = seq.progress_pct
                elapsed = seq.elapsed_ms
                total = seq.total_ms
                e_min, e_sec = elapsed // 60000, (elapsed % 60000) // 1000
                t_min, t_sec = total // 60000, (total % 60000) // 1000
                print(
                    f"\r[{pct:3d}%] {e_min}:{e_sec:02d} / {t_min}:{t_sec:02d}",
                    end="",
                    flush=True,
                )

    except KeyboardInterrupt:
        pass
    finally:
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
    current_ms = 1  # Start at 1 to avoid start_ms re-initialization issue
    chunk_ms = CHUNK_SIZE * 1000 // SAMPLE_RATE

    while seq.playing:
        samples = seq.generate_chunk(CHUNK_SIZE, current_ms)
        audio = Mixer.to_float32(samples)
        # Convert to 16-bit PCM
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
        "-t", "--tracks", type=int, default=3, help="Max tracks (default: 3)"
    )
    parser.add_argument("-o", "--output", help="Export to WAV file")
    parser.add_argument("--mute", action="store_true", help="Mute audio output")
    args = parser.parse_args()

    seq = Sequencer()
    num_tracks = seq.load_midi(args.input, args.tracks)
    print(f"Loaded: {args.input}")
    print(f"Tracks: {num_tracks}, Duration: {seq.total_ms // 1000}s")

    if args.output:
        export_wav(seq, args.output)
    else:
        play_audio(seq, mute=args.mute)


if __name__ == "__main__":
    main()
