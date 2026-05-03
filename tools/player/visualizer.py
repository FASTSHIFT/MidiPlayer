"""
Waveform Visualizer — real-time matplotlib display with playback controls.

Features:
- 5 waveform subplots (CH0~CH2 + NOISE + MIX)
- Rectangle-based volume bars and ADSR stage indicators
- Draggable Slider progress bar with seek
- Pause/Resume and speed control buttons + keyboard shortcuts
"""

import sys
import numpy as np
import threading
import matplotlib

_INTERACTIVE_BACKENDS = ["TkAgg", "Qt5Agg", "QtAgg", "GTK3Agg", "GTK4Agg", "macosx"]
_backend_ok = False
for _backend in _INTERACTIVE_BACKENDS:
    try:
        matplotlib.use(_backend, force=True)
        __import__(f"matplotlib.backends.backend_{_backend.lower()}")
        _backend_ok = True
        break
    except (ImportError, ModuleNotFoundError):
        continue

if not _backend_ok:
    matplotlib.use("Agg")

from .mixer import NUM_CHANNELS

NUM_MELODIC = NUM_CHANNELS - 1

# Display constants
WAVEFORM_SYMBOLS = ["SQR", "TRI", "SAW", "PLS"]
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ADSR_STAGE_NAMES = ["Atk", "Dec", "Sus", "Rel"]  # full-ish names for the 4 rects
ADSR_ACTIVE_COLORS = ["#2196F3", "#FF9800", "#4CAF50", "#F44336"]  # A D S R
ADSR_INACTIVE = "#2a2a4a"
SPEED_OPTIONS = [0.5, 1.0, 1.5, 2.0]


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
    return f"{name}{octave}".rjust(3)


class Visualizer:
    """Real-time waveform visualization with playback controls."""

    def __init__(self, sequencer):
        self.seq = sequencer
        self.num_channels = NUM_CHANNELS
        self.num_plots = NUM_CHANNELS + 1  # channels + MIX
        self.display_samples = 512
        self.running = False
        self._seeking = False  # True while user drags slider

        self._ch_buffers = [
            np.zeros(self.display_samples, dtype=np.int16)
            for _ in range(self.num_channels)
        ]
        self._mix_buffer = np.zeros(self.display_samples, dtype=np.uint16)
        self._lock = threading.Lock()

    def update_buffers(self, ch_samples, mix_samples):
        """Called from audio thread to push new waveform data."""
        with self._lock:
            n = min(len(mix_samples), self.display_samples)
            for i in range(self.num_channels):
                if i < len(ch_samples):
                    self._ch_buffers[i] = np.roll(self._ch_buffers[i], -n)
                    self._ch_buffers[i][-n:] = ch_samples[i][-n:]
            self._mix_buffer = np.roll(self._mix_buffer, -n)
            self._mix_buffer[-n:] = mix_samples[-n:]

    def run(self, update_interval_ms=30):
        """Start the visualization window (blocks until closed)."""
        if not _backend_ok:
            print(
                "Error: No interactive matplotlib backend available.\n"
                "Install one of:\n"
                "  sudo apt install python3-tk\n"
                "  pip install PyQt5\n",
                file=sys.stderr,
            )
            self.running = False
            return

        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        from matplotlib.widgets import Slider, Button
        from matplotlib.patches import Rectangle

        self.running = False
        seq = self.seq

        # --- Layout ---
        fig = plt.figure(figsize=(12, 2.0 * self.num_plots + 1.2), facecolor="#1a1a2e")
        fig.suptitle("MidiPlayer Visualizer", color="white", fontsize=14, y=0.98)

        # GridSpec: waveform rows + control row at bottom
        gs = fig.add_gridspec(
            self.num_plots + 1,
            1,
            height_ratios=[1] * self.num_plots + [0.15],
            hspace=0.35,
            top=0.95,
            bottom=0.02,
            left=0.07,
            right=0.98,
        )

        axes = [fig.add_subplot(gs[i]) for i in range(self.num_plots)]
        ax_ctrl = fig.add_subplot(gs[self.num_plots])
        ax_ctrl.set_visible(False)  # just a spacer

        lines = []
        info_texts = []
        vol_bars = []  # Rectangle patches for volume
        adsr_rects = []  # list of 4 Rectangles per channel
        x = np.arange(self.display_samples)

        ch_colors = [
            "#00d2ff",  # CH0
            "#ff6b6b",  # CH1
            "#ffd93d",  # CH2
            "#6bcb77",  # CH3
            "#ff9a3c",  # CH4
            "#a78bfa",  # CH5
            "#f472b6",  # CH6
            "#b388ff",  # NOISE
            "#e94560",  # MIX
        ]

        for i, ax in enumerate(axes):
            ax.set_facecolor("#16213e")
            ax.tick_params(colors="gray", labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#333")

            is_mix = i == self.num_plots - 1

            if is_mix:
                ax.set_ylim(0, 1023)
                ax.axhline(y=512, color="#333", linewidth=0.5, linestyle="--")
                ax.set_ylabel("MIX", color=ch_colors[-1], fontsize=10)
                (line,) = ax.plot(
                    x,
                    np.full(self.display_samples, 512),
                    color=ch_colors[-1],
                    linewidth=0.8,
                )
            else:
                ax.set_ylim(-140, 140)
                label = f"CH{i}" if i < NUM_MELODIC else "NOISE"
                ax.set_ylabel(label, color=ch_colors[i], fontsize=10)
                (line,) = ax.plot(
                    x,
                    np.zeros(self.display_samples),
                    color=ch_colors[i],
                    linewidth=0.8,
                )

            ax.set_xlim(0, self.display_samples)
            lines.append(line)

            # Info text (note + waveform for melodic, LFSR for noise)
            info = ax.text(
                0.01,
                0.92,
                "",
                transform=ax.transAxes,
                ha="left",
                va="top",
                color="white",
                fontsize=9,
                fontfamily="monospace",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#0f3460", alpha=0.85),
            )
            info_texts.append(info)

            if not is_mix:
                # Volume bar — inset axes in top-right
                ax_vol = ax.inset_axes([0.88, 0.75, 0.10, 0.15])
                ax_vol.set_xlim(0, 127)
                ax_vol.set_ylim(0, 1)
                ax_vol.axis("off")
                bg = Rectangle((0, 0), 127, 1, facecolor=ADSR_INACTIVE, linewidth=0)
                ax_vol.add_patch(bg)
                vbar = Rectangle((0, 0), 0, 1, facecolor=ch_colors[i], linewidth=0)
                ax_vol.add_patch(vbar)
                vol_bars.append(vbar)

                # ADSR stage indicator — 4 small rects
                ax_adsr = ax.inset_axes([0.72, 0.75, 0.14, 0.15])
                ax_adsr.set_xlim(0, 4)
                ax_adsr.set_ylim(0, 1)
                ax_adsr.axis("off")
                ch_adsr = []
                for j in range(4):
                    r = Rectangle(
                        (j * 1.0 + 0.05, 0.1),
                        0.9,
                        0.8,
                        facecolor=ADSR_INACTIVE,
                        linewidth=0,
                    )
                    ax_adsr.add_patch(r)
                    ax_adsr.text(
                        j * 1.0 + 0.5,
                        0.5,
                        ADSR_STAGE_NAMES[j],
                        ha="center",
                        va="center",
                        fontsize=6,
                        color="#666",
                        fontfamily="monospace",
                    )
                    ch_adsr.append(r)
                adsr_rects.append(ch_adsr)
            else:
                vol_bars.append(None)
                adsr_rects.append(None)

        # --- Controls ---
        # Slider
        ax_slider = fig.add_axes([0.18, 0.025, 0.52, 0.018], facecolor="#16213e")
        slider = Slider(
            ax_slider,
            "",
            0,
            100,
            valinit=0,
            color="#e94560",
            track_color="#2a2a4a",
        )
        slider.valtext.set_visible(False)

        # Time text
        time_text = fig.text(
            0.72,
            0.033,
            "0:00 / 0:00",
            color="white",
            fontsize=10,
            fontfamily="monospace",
            va="center",
        )

        # Pause button
        ax_pause = fig.add_axes([0.05, 0.015, 0.05, 0.03])
        btn_pause = Button(ax_pause, ">", color="#16213e", hovercolor="#2a2a4a")
        btn_pause.label.set_color("white")
        btn_pause.label.set_fontsize(12)

        # Speed button
        ax_speed = fig.add_axes([0.12, 0.015, 0.05, 0.03])
        btn_speed = Button(ax_speed, "1.0x", color="#16213e", hovercolor="#2a2a4a")
        btn_speed.label.set_color("white")
        btn_speed.label.set_fontsize(9)

        # Speed index tracker
        speed_state = {"idx": SPEED_OPTIONS.index(1.0)}

        # --- Callbacks ---
        def on_pause_click(_event):
            seq.toggle_pause()
            btn_pause.label.set_text(">" if seq.paused else "||")
            fig.canvas.draw_idle()

        def on_speed_click(_event):
            speed_state["idx"] = (speed_state["idx"] + 1) % len(SPEED_OPTIONS)
            seq.speed = SPEED_OPTIONS[speed_state["idx"]]
            btn_speed.label.set_text(f"{seq.speed:.1f}x")
            fig.canvas.draw_idle()

        def on_slider_changed(val):
            if self._seeking:
                target_ms = int(val * seq.total_ms / 100)
                seq.seek(target_ms)

        def on_slider_press(_event):
            self._seeking = True

        def on_slider_release(_event):
            self._seeking = False

        def on_key(event):
            if event.key == " ":
                on_pause_click(None)
            elif event.key == "right":
                seq.seek(seq.elapsed_ms + 5000)
            elif event.key == "left":
                seq.seek(max(0, seq.elapsed_ms - 5000))
            elif event.key == "]":
                seq.speed = min(seq.speed + 0.5, 4.0)
                btn_speed.label.set_text(f"{seq.speed:.1f}x")
            elif event.key == "[":
                seq.speed = max(seq.speed - 0.5, 0.25)
                btn_speed.label.set_text(f"{seq.speed:.1f}x")
            elif event.key == "r":
                seq.seek(0)

        btn_pause.on_clicked(on_pause_click)
        btn_speed.on_clicked(on_speed_click)
        slider.on_changed(on_slider_changed)
        ax_slider.figure.canvas.mpl_connect(
            "button_press_event",
            lambda e: on_slider_press(e) if e.inaxes == ax_slider else None,
        )
        ax_slider.figure.canvas.mpl_connect(
            "button_release_event",
            lambda e: on_slider_release(e) if self._seeking else None,
        )
        fig.canvas.mpl_connect("key_press_event", on_key)

        mix_idx = self.num_plots - 1

        # --- Animation ---
        def animate(_frame):
            with self._lock:
                # Melodic channels
                for i in range(NUM_MELODIC):
                    lines[i].set_ydata(self._ch_buffers[i])
                    osc = seq.oscillators[i]
                    env = seq.envelopes[i]
                    note = phase_inc_to_note_name(int(osc.phase_inc))
                    wf_idx = int(osc.waveform)
                    wf = (
                        WAVEFORM_SYMBOLS[wf_idx]
                        if wf_idx < len(WAVEFORM_SYMBOLS)
                        else "?"
                    )
                    info_texts[i].set_text(f"{note}  {wf}")

                    # Volume bar
                    vol_bars[i].set_width(env.level)

                    # ADSR rects
                    stage = int(env.stage)
                    for j in range(4):
                        if stage > 0 and j == stage - 1:
                            adsr_rects[i][j].set_facecolor(ADSR_ACTIVE_COLORS[j])
                        else:
                            adsr_rects[i][j].set_facecolor(ADSR_INACTIVE)

                # Noise channel
                ni = NUM_MELODIC
                lines[ni].set_ydata(self._ch_buffers[ni])
                noise_env = seq.envelopes[ni]
                info_texts[ni].set_text("LFSR Noise")
                vol_bars[ni].set_width(noise_env.level)
                noise_stage = int(noise_env.stage)
                for j in range(4):
                    if noise_stage > 0 and j == noise_stage - 1:
                        adsr_rects[ni][j].set_facecolor(ADSR_ACTIVE_COLORS[j])
                    else:
                        adsr_rects[ni][j].set_facecolor(ADSR_INACTIVE)

                # MIX
                lines[mix_idx].set_ydata(self._mix_buffer)
                pct = seq.progress_pct
                info_texts[mix_idx].set_text(f"{pct}%")

                # Slider + time (don't update slider while user is dragging)
                if not self._seeking:
                    slider.set_val(pct)

                elapsed = seq.elapsed_ms
                total = seq.total_ms
                e_min, e_sec = elapsed // 60000, (elapsed % 60000) // 1000
                t_min, t_sec = total // 60000, (total % 60000) // 1000
                time_text.set_text(f"{e_min}:{e_sec:02d} / {t_min}:{t_sec:02d}")

                # Pause button icon
                btn_pause.label.set_text(">" if seq.paused else "||")

        _anim = animation.FuncAnimation(  # noqa: F841
            fig,
            animate,
            interval=update_interval_ms,
            blit=False,
            cache_frame_data=False,
        )

        self.running = True
        plt.show()
        self.running = False
