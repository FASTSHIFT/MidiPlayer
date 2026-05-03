"""
Waveform Visualizer — real-time matplotlib display of synthesis channels.

Shows all channels (3 melodic + 1 noise), ADSR state, and mixed output
with progress bar.
"""

import sys
import numpy as np
import threading
import matplotlib

# Select an interactive backend before importing pyplot.
# Agg is non-interactive (render-only) and cannot call plt.show().
_INTERACTIVE_BACKENDS = ["TkAgg", "Qt5Agg", "QtAgg", "GTK3Agg", "GTK4Agg", "macosx"]
_backend_ok = False
for _backend in _INTERACTIVE_BACKENDS:
    try:
        matplotlib.use(_backend, force=True)
        # Verify the backend actually loads (catches missing tkinter etc.)
        __import__(f"matplotlib.backends.backend_{_backend.lower()}")
        _backend_ok = True
        break
    except (ImportError, ModuleNotFoundError):
        continue

if not _backend_ok:
    # Stay on default Agg — run() will print a helpful error instead of crashing
    matplotlib.use("Agg")

from .mixer import NUM_CHANNELS

NUM_MELODIC = NUM_CHANNELS - 1  # 3 melodic, 1 noise

# Waveform and note name lookups
WAVEFORM_NAMES = ["Square", "Triangle", "Sawtooth", "Pulse25"]
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
STAGE_NAMES = ["IDLE", "ATK", "DEC", "SUS", "REL"]
STAGE_COLORS = ["gray", "#2196F3", "#FF9800", "#4CAF50", "#F44336"]


def phase_inc_to_note_name(phase_inc):
    """Convert phase increment back to approximate note name."""
    if phase_inc == 0:
        return "---"
    freq = phase_inc * 16000 / 65536
    if freq < 16:
        return "---"
    import math

    midi = 69 + 12 * math.log2(freq / 440.0)
    midi = round(midi)
    if midi < 0 or midi > 127:
        return "---"
    octave = midi // 12 - 1
    name = NOTE_NAMES[midi % 12]
    return f"{name}{octave}"


class Visualizer:
    """Real-time waveform visualization using matplotlib."""

    def __init__(self, sequencer):
        self.seq = sequencer
        self.num_channels = NUM_CHANNELS  # 3 melodic + 1 noise
        self.num_plots = NUM_CHANNELS + 1  # all channels + mixed output
        self.display_samples = 512
        self.running = False

        # Ring buffers: one per channel (melodic + noise)
        self._ch_buffers = [
            np.zeros(self.display_samples, dtype=np.int16)
            for _ in range(self.num_channels)
        ]
        self._mix_buffer = np.zeros(self.display_samples, dtype=np.uint16)
        self._lock = threading.Lock()

    def update_buffers(self, ch_samples, mix_samples):
        """Called from audio thread to push new waveform data.

        Args:
            ch_samples: list of int16 arrays, one per channel
                        (3 melodic + 1 noise = 4 total)
            mix_samples: uint16 array of mixed output
        """
        with self._lock:
            n = min(len(mix_samples), self.display_samples)
            for i in range(self.num_channels):
                if i < len(ch_samples):
                    self._ch_buffers[i] = np.roll(self._ch_buffers[i], -n)
                    self._ch_buffers[i][-n:] = ch_samples[i][-n:]
            self._mix_buffer = np.roll(self._mix_buffer, -n)
            self._mix_buffer[-n:] = mix_samples[-n:]

    def run(self, update_interval_ms=50):
        """Start the visualization window (blocks until closed)."""
        if not _backend_ok:
            print(
                "Error: No interactive matplotlib backend available.\n"
                "Install one of the following:\n"
                "  sudo apt install python3-tk    # TkAgg (recommended)\n"
                "  pip install PyQt5              # Qt5Agg\n",
                file=sys.stderr,
            )
            self.running = False
            return

        import matplotlib.pyplot as plt
        import matplotlib.animation as animation

        self.running = True

        fig, axes = plt.subplots(
            self.num_plots,
            1,
            figsize=(10, 1.8 * self.num_plots + 0.5),
            facecolor="#1a1a2e",
        )
        fig.suptitle("MidiPlayer Visualizer", color="white", fontsize=14)
        fig.tight_layout(rect=[0.05, 0.04, 1.0, 0.95], h_pad=1.5)

        lines = []
        labels = []
        x = np.arange(self.display_samples)

        # Colors: CH0, CH1, CH2, NOISE, MIX
        colors = ["#00d2ff", "#ff6b6b", "#ffd93d", "#b388ff", "#e94560"]

        for i, ax in enumerate(axes):
            ax.set_facecolor("#16213e")
            ax.tick_params(colors="gray", labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#333")

            if i < NUM_MELODIC:
                ax.set_ylim(-140, 140)
                ax.set_ylabel(f"CH{i}", color=colors[i], fontsize=10)
                (line,) = ax.plot(
                    x, np.zeros(self.display_samples), color=colors[i], linewidth=0.8
                )
            elif i == NUM_MELODIC:
                ax.set_ylim(-140, 140)
                ax.set_ylabel("NOISE", color=colors[i], fontsize=10)
                (line,) = ax.plot(
                    x, np.zeros(self.display_samples), color=colors[i], linewidth=0.8
                )
            else:
                ax.set_ylim(0, 1023)
                ax.axhline(y=512, color="#333", linewidth=0.5, linestyle="--")
                ax.set_ylabel("MIX", color=colors[-1], fontsize=10)
                (line,) = ax.plot(
                    x,
                    np.full(self.display_samples, 512),
                    color=colors[-1],
                    linewidth=0.8,
                )

            label = ax.text(
                0.98,
                0.90,
                "",
                transform=ax.transAxes,
                ha="right",
                va="top",
                color="white",
                fontsize=9,
                fontfamily="monospace",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#0f3460", alpha=0.8),
            )

            ax.set_xlim(0, self.display_samples)
            lines.append(line)
            labels.append(label)

        # Progress bar — inside the MIX axes (bottom-center) so blit works
        mix_ax = axes[-1]
        progress_text = mix_ax.text(
            0.5,
            0.08,
            "",
            transform=mix_ax.transAxes,
            ha="center",
            va="bottom",
            color="white",
            fontsize=10,
            fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a1a2e", alpha=0.85),
        )

        num_ch = self.num_channels
        mix_idx = num_ch  # index of MIX subplot

        def animate(_frame):
            with self._lock:
                # Melodic channels
                for i in range(NUM_MELODIC):
                    lines[i].set_ydata(self._ch_buffers[i])
                    osc = self.seq.oscillators[i]
                    env = self.seq.envelopes[i]
                    note = phase_inc_to_note_name(int(osc.phase_inc))
                    wf = (
                        WAVEFORM_NAMES[int(osc.waveform)]
                        if int(osc.waveform) < len(WAVEFORM_NAMES)
                        else "?"
                    )
                    stage = (
                        STAGE_NAMES[int(env.stage)]
                        if int(env.stage) < len(STAGE_NAMES)
                        else "?"
                    )
                    labels[i].set_text(f"{note}  {wf}  [{stage}] vol={env.level}")

                # Noise channel
                noise_idx = NUM_MELODIC
                lines[noise_idx].set_ydata(self._ch_buffers[noise_idx])
                noise_env = self.seq.envelopes[noise_idx]
                noise_stage = (
                    STAGE_NAMES[int(noise_env.stage)]
                    if int(noise_env.stage) < len(STAGE_NAMES)
                    else "?"
                )
                labels[noise_idx].set_text(
                    f"LFSR  [{noise_stage}] vol={noise_env.level}"
                )

                # Mixed output
                lines[mix_idx].set_ydata(self._mix_buffer)

                # Progress
                pct = self.seq.progress_pct
                elapsed = self.seq.elapsed_ms
                total = self.seq.total_ms
                e_min, e_sec = elapsed // 60000, (elapsed % 60000) // 1000
                t_min, t_sec = total // 60000, (total % 60000) // 1000

                bar_len = 30
                filled = pct * bar_len // 100
                bar = "█" * filled + "░" * (bar_len - filled)
                labels[mix_idx].set_text(f"{pct}%")
                progress_text.set_text(
                    f"{bar}  {e_min}:{e_sec:02d} / {t_min}:{t_sec:02d}"
                )

            return lines + labels + [progress_text]

        _anim = animation.FuncAnimation(  # noqa: F841
            fig, animate, interval=update_interval_ms, blit=True, cache_frame_data=False
        )

        plt.show()
        self.running = False
