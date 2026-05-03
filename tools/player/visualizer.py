"""
Waveform Visualizer — single-axes stacked layout with pure blit.

All waveforms, volume bars, ADSR indicators, and progress bar are drawn
in one Axes as animated artists. No matplotlib widgets (Slider/Button)
to avoid blit conflicts. Controls via keyboard shortcuts only.

Keyboard:
  Space     Pause / Resume
  Left/Right  Seek ±5s
  [ / ]     Speed down / up
  R         Reset to start
"""

import sys
import time as _time
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

# Display constants
WAVEFORM_SYMBOLS = ["SQR", "TRI", "SAW", "PLS"]
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ADSR_STAGE_NAMES = ["Atk", "Dec", "Sus", "Rel"]
ADSR_ACTIVE_COLORS = ["#2196F3", "#FF9800", "#4CAF50", "#F44336"]
ADSR_INACTIVE = "#2a2a4a"
SPEED_OPTIONS = [0.5, 1.0, 1.5, 2.0]
CHANNEL_SPACING = 300

_PRESET_COLORS = [
    "#00d2ff",
    "#ff6b6b",
    "#ffd93d",
    "#6bcb77",
    "#ff9a3c",
    "#a78bfa",
    "#f472b6",
    "#b388ff",
]
_MIX_COLOR = "#e94560"


def _make_colors(num_channels):
    """Generate channel colors: preset for <=8, colormap for more."""
    if num_channels <= len(_PRESET_COLORS):
        return _PRESET_COLORS[:num_channels] + [_MIX_COLOR]
    import matplotlib as mpl

    cmap = mpl.colormaps.get_cmap("tab20").resampled(num_channels)
    colors = [
        "#{:02x}{:02x}{:02x}".format(int(c[0] * 255), int(c[1] * 255), int(c[2] * 255))
        for c in [cmap(i) for i in range(num_channels)]
    ]
    return colors + [_MIX_COLOR]


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
    """Real-time waveform visualization — pure blit, keyboard controls."""

    def __init__(self, sequencer):
        self.seq = sequencer
        self.num_channels = sequencer.num_channels
        self.num_melodic = sequencer.num_melodic
        self.num_plots = self.num_channels + 1
        self.display_samples = 512
        self.running = False
        self._seeking = False

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
        from matplotlib.patches import Rectangle

        seq = self.seq
        sp = CHANNEL_SPACING
        ns = self.display_samples
        n_total = self.num_plots
        colors = _make_colors(self.num_channels)

        # --- Figure + single Axes ---
        fig_h = max(6, min(1.2 * n_total + 1.0, 16))
        fig = plt.figure(figsize=(13, fig_h), facecolor="#1a1a2e")
        ax = fig.add_axes([0.06, 0.06, 0.92, 0.92], facecolor="#16213e")

        # Layout dimensions
        vol_x = ns + 8
        vol_w_max = 25
        vol_h = sp * 0.22
        adsr_x = vol_x + vol_w_max + 5
        adsr_w = 10
        adsr_gap = 2
        x_max = adsr_x + 4 * (adsr_w + adsr_gap) + 10
        prog_y = -sp * 0.6
        prog_h = sp * 0.12
        y_min = prog_y - sp * 0.3
        y_max = n_total * sp + sp * 0.5

        ax.set_xlim(0, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_yticks([])
        ax.tick_params(axis="x", colors="gray", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#333")

        x = np.arange(ns)

        # --- Static elements ---
        for i in range(n_total):
            yc = i * sp
            if i > 0:
                ax.axhline(y=yc - sp // 2, color="#333", lw=0.5, ls="--")
            is_mix = i == n_total - 1
            is_noise = i == self.num_melodic
            lbl = "MIX" if is_mix else ("NOISE" if is_noise else f"CH{i}")
            clr = _MIX_COLOR if is_mix else colors[i]
            ax.text(
                -5,
                yc,
                lbl,
                ha="right",
                va="center",
                fontsize=8,
                color=clr,
                fontfamily="monospace",
                clip_on=False,
            )

        ax.axhline(y=(n_total - 1) * sp, color="#444", lw=0.3, ls=":")

        # Help text
        ax.text(
            x_max - 2,
            y_max - 10,
            "Space:pause  []:speed  R:reset  Left/Right:seek",
            ha="right",
            va="top",
            fontsize=6,
            color="#555",
            fontfamily="monospace",
        )

        # --- Animated artists ---
        lines = []
        info_texts = []
        vol_rects = []
        adsr_rects_all = []
        all_artists = []

        for i in range(n_total):
            yc = i * sp
            is_mix = i == n_total - 1
            c = _MIX_COLOR if is_mix else colors[i]

            init_y = np.full(ns, float(yc))
            (line,) = ax.plot(x, init_y, color=c, lw=0.8, animated=True)
            lines.append(line)
            all_artists.append(line)

            txt = ax.text(
                5,
                yc + sp * 0.35,
                "",
                fontsize=7,
                color="white",
                fontfamily="monospace",
                va="center",
                animated=True,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="#0f3460", alpha=0.8),
            )
            info_texts.append(txt)
            all_artists.append(txt)

            if not is_mix:
                bg = Rectangle(
                    (vol_x, yc - vol_h / 2),
                    vol_w_max,
                    vol_h,
                    facecolor=ADSR_INACTIVE,
                    lw=0,
                    animated=True,
                )
                ax.add_patch(bg)
                vbar = Rectangle(
                    (vol_x, yc - vol_h / 2),
                    0,
                    vol_h,
                    facecolor=c,
                    lw=0,
                    animated=True,
                )
                ax.add_patch(vbar)
                vol_rects.append((bg, vbar))
                all_artists.extend([bg, vbar])

                ch_adsr = []
                adsr_h = sp * 0.18
                for j in range(4):
                    rx = adsr_x + j * (adsr_w + adsr_gap)
                    r = Rectangle(
                        (rx, yc - adsr_h / 2),
                        adsr_w,
                        adsr_h,
                        facecolor=ADSR_INACTIVE,
                        lw=0,
                        animated=True,
                    )
                    ax.add_patch(r)
                    ch_adsr.append(r)
                    all_artists.append(r)
                    ax.text(
                        rx + adsr_w / 2,
                        yc - adsr_h / 2 - 6,
                        ADSR_STAGE_NAMES[j],
                        ha="center",
                        va="top",
                        fontsize=5,
                        color="#555",
                        fontfamily="monospace",
                    )
                adsr_rects_all.append(ch_adsr)
            else:
                vol_rects.append(None)
                adsr_rects_all.append(None)

        # Progress bar (Rectangle in main axes)
        prog_bg = Rectangle(
            (0, prog_y),
            ns,
            prog_h,
            facecolor="#2a2a4a",
            lw=0,
            animated=True,
        )
        ax.add_patch(prog_bg)
        prog_fg = Rectangle(
            (0, prog_y),
            0,
            prog_h,
            facecolor="#e94560",
            lw=0,
            animated=True,
        )
        ax.add_patch(prog_fg)
        all_artists.extend([prog_bg, prog_fg])

        # Status text (time + speed + fps)
        status_txt = ax.text(
            ns / 2,
            prog_y - 12,
            "",
            ha="center",
            va="top",
            fontsize=8,
            color="white",
            fontfamily="monospace",
            animated=True,
        )
        all_artists.append(status_txt)

        # --- Keyboard callbacks ---
        def on_key(event):
            if event.key == " ":
                seq.toggle_pause()
            elif event.key == "right":
                seq.seek(seq.elapsed_ms + 5000)
            elif event.key == "left":
                seq.seek(max(0, seq.elapsed_ms - 5000))
            elif event.key == "]":
                seq.speed = min(seq.speed + 0.5, 4.0)
            elif event.key == "[":
                seq.speed = max(seq.speed - 0.5, 0.25)
            elif event.key == "r":
                seq.seek(0)

        fig.canvas.mpl_connect("key_press_event", on_key)

        # --- Initial draw + capture FULL figure background ---
        fig.canvas.draw()
        bg_cache = fig.canvas.copy_from_bbox(fig.bbox)

        mix_idx = n_total - 1
        fps_state = {"last": _time.time(), "count": 0, "fps": 0.0}

        # Recapture background on resize
        def on_resize(_event):
            nonlocal bg_cache
            fig.canvas.draw()
            bg_cache = fig.canvas.copy_from_bbox(fig.bbox)

        fig.canvas.mpl_connect("resize_event", on_resize)

        # --- Timer-driven animation (no FuncAnimation, no draw_idle) ---
        def animate():
            fig.canvas.restore_region(bg_cache)

            with self._lock:
                for i in range(self.num_melodic):
                    yoff = i * sp
                    lines[i].set_ydata(self._ch_buffers[i].astype(np.float64) + yoff)
                    osc = seq.oscillators[i]
                    env = seq.envelopes[i]
                    note = phase_inc_to_note_name(int(osc.phase_inc))
                    wf_idx = int(osc.waveform)
                    wf = WAVEFORM_SYMBOLS[wf_idx] if wf_idx < 4 else "?"
                    info_texts[i].set_text(f"{note} {wf}")
                    _, vbar = vol_rects[i]
                    vbar.set_width(env.level * vol_w_max / 127)
                    stage = int(env.stage)
                    for j in range(4):
                        c = (
                            ADSR_ACTIVE_COLORS[j]
                            if (stage > 0 and j == stage - 1)
                            else ADSR_INACTIVE
                        )
                        adsr_rects_all[i][j].set_facecolor(c)

                ni = self.num_melodic
                lines[ni].set_ydata(self._ch_buffers[ni].astype(np.float64) + ni * sp)
                noise_env = seq.envelopes[ni]
                info_texts[ni].set_text("LFSR")
                _, nvbar = vol_rects[ni]
                nvbar.set_width(noise_env.level * vol_w_max / 127)
                ns_ = int(noise_env.stage)
                for j in range(4):
                    c = (
                        ADSR_ACTIVE_COLORS[j]
                        if (ns_ > 0 and j == ns_ - 1)
                        else ADSR_INACTIVE
                    )
                    adsr_rects_all[ni][j].set_facecolor(c)

                mix_yoff = mix_idx * sp
                lines[mix_idx].set_ydata(
                    (self._mix_buffer.astype(np.float64) - 512) + mix_yoff
                )
                pct = seq.progress_pct
                info_texts[mix_idx].set_text(f"{pct}%")

                prog_fg.set_width(pct * ns / 100)

            # Status line
            elapsed = seq.elapsed_ms
            total = seq.total_ms
            e_min, e_sec = elapsed // 60000, (elapsed % 60000) // 1000
            t_min, t_sec = total // 60000, (total % 60000) // 1000
            paused = " PAUSED" if seq.paused else ""
            spd = f" {seq.speed:.1f}x" if seq.speed != 1.0 else ""
            status_txt.set_text(
                f"{e_min}:{e_sec:02d} / {t_min}:{t_sec:02d}"
                f"{spd}{paused}  {fps_state['fps']:.0f}fps"
            )

            for artist in all_artists:
                ax.draw_artist(artist)
            fig.canvas.blit(fig.bbox)
            fig.canvas.flush_events()

            # FPS
            fps_state["count"] += 1
            now = _time.time()
            dt = now - fps_state["last"]
            if dt >= 1.0:
                fps_state["fps"] = fps_state["count"] / dt
                fps_state["count"] = 0
                fps_state["last"] = now

        timer = fig.canvas.new_timer(interval=update_interval_ms)
        timer.add_callback(animate)
        timer.start()

        self.running = True
        plt.show()
        timer.stop()
        self.running = False
