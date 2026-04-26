"""
Typeflow GUI — A modern desktop app for human-like typing simulation.
Built with customtkinter for a polished, dark-mode interface.

Run:  python typeflow_gui.py
Build: pyinstaller --onefile --windowed --name Typeflow typeflow_gui.py
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

# Ensure the engine module can be found when running as a PyInstaller bundle
if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _base)

from typeflow_engine import (
    TypingProfile, estimate_time, format_duration, type_text,
    compute_minimum_time, solve_profile_for_time,
)

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT_FAMILY = "Segoe UI"
COLOR_BG = "#0f0f14"
COLOR_CARD = "#1a1a24"
COLOR_CARD_HOVER = "#22222e"
COLOR_ACCENT = "#6c5ce7"
COLOR_ACCENT_HOVER = "#7e6ff0"
COLOR_RED = "#e74c3c"
COLOR_RED_HOVER = "#ff6b5a"
COLOR_GREEN = "#00b894"
COLOR_YELLOW = "#f0c040"
COLOR_TEXT = "#e8e8f0"
COLOR_TEXT_DIM = "#8888a0"
COLOR_BORDER = "#2a2a3a"
COLOR_INPUT_BG = "#12121c"


class TypeflowApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("Typeflow")
        self.geometry("960x700")
        self.minsize(860, 620)
        self.configure(fg_color=COLOR_BG)

        self._typing_thread = None
        self._stop_flag = False
        self._is_running = False
        self._auto_mode = True           # True = desired-time drives sliders
        self._suppressing_trace = False  # prevent recursive slider updates
        self._default_est_seconds = 0.0  # estimate with default profile
        self._min_time_seconds = 0.0     # absolute floor

        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        # --- Top bar ---
        top = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=0, height=56)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(
            top, text="TYPEFLOW",
            font=(FONT_FAMILY, 20, "bold"), text_color=COLOR_ACCENT,
        ).pack(side="left", padx=20)

        ctk.CTkLabel(
            top, text="Human-like typing simulator",
            font=(FONT_FAMILY, 12), text_color=COLOR_TEXT_DIM,
        ).pack(side="left", padx=(0, 20))

        safety_label = ctk.CTkLabel(
            top,
            text="Move mouse to top-left corner to ABORT",
            font=(FONT_FAMILY, 11), text_color=COLOR_RED,
        )
        safety_label.pack(side="right", padx=20)

        # --- Main content: two columns ---
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(12, 8))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # ====== LEFT COLUMN — Text input ======
        left = ctk.CTkFrame(body, fg_color=COLOR_CARD, corner_radius=12,
                            border_width=1, border_color=COLOR_BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        left_header = ctk.CTkFrame(left, fg_color="transparent")
        left_header.pack(fill="x", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            left_header, text="Text to Type",
            font=(FONT_FAMILY, 14, "bold"), text_color=COLOR_TEXT,
        ).pack(side="left")

        btn_frame = ctk.CTkFrame(left_header, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(
            btn_frame, text="Load File", width=90, height=30,
            font=(FONT_FAMILY, 12), corner_radius=8,
            fg_color=COLOR_BORDER, hover_color=COLOR_CARD_HOVER,
            command=self._load_file,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="Paste", width=70, height=30,
            font=(FONT_FAMILY, 12), corner_radius=8,
            fg_color=COLOR_BORDER, hover_color=COLOR_CARD_HOVER,
            command=self._paste_clipboard,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="Clear", width=60, height=30,
            font=(FONT_FAMILY, 12), corner_radius=8,
            fg_color=COLOR_BORDER, hover_color=COLOR_CARD_HOVER,
            command=self._clear_text,
        ).pack(side="left")

        self.text_box = ctk.CTkTextbox(
            left, font=(FONT_FAMILY, 13), corner_radius=8,
            fg_color=COLOR_INPUT_BG, text_color=COLOR_TEXT,
            border_width=1, border_color=COLOR_BORDER,
            wrap="word",
        )
        self.text_box.pack(fill="both", expand=True, padx=16, pady=(6, 14))
        self.text_box.bind("<KeyRelease>", lambda e: self._update_stats())

        # ====== RIGHT COLUMN — Settings ======
        right = ctk.CTkScrollableFrame(
            body, fg_color=COLOR_CARD, corner_radius=12,
            border_width=1, border_color=COLOR_BORDER,
            scrollbar_button_color=COLOR_BORDER,
            scrollbar_button_hover_color=COLOR_ACCENT,
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(
            right, text="Settings",
            font=(FONT_FAMILY, 14, "bold"), text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=16, pady=(14, 10))

        # -- Sliders --
        self.speed_var = tk.DoubleVar(value=1.0)
        self._make_slider(right, "Speed Multiplier", self.speed_var,
                          0.3, 3.0, "x", resolution=0.1)

        self.wpm_var = tk.DoubleVar(value=55.0)
        self._make_slider(right, "Base WPM", self.wpm_var,
                          20, 120, "wpm", resolution=5)

        self.error_var = tk.DoubleVar(value=1.2)
        self._make_slider(right, "Typo Rate", self.error_var,
                          0.0, 8.0, "%", resolution=0.1)

        self.thinking_var = tk.DoubleVar(value=0.8)
        self._make_slider(right, "Thinking Pauses", self.thinking_var,
                          0.0, 5.0, "%", resolution=0.1)

        self.distraction_var = tk.DoubleVar(value=0.1)
        self._make_slider(right, "Distraction Breaks", self.distraction_var,
                          0.0, 2.0, "%", resolution=0.05)

        self.save_var = tk.IntVar(value=300)
        self._make_slider(right, "Save Pause Interval", self.save_var,
                          50, 1000, "chars", resolution=50)

        self.countdown_var = tk.IntVar(value=5)
        self._make_slider(right, "Countdown", self.countdown_var,
                          3, 15, "sec", resolution=1)

        # -- Separator --
        sep = ctk.CTkFrame(right, fg_color=COLOR_BORDER, height=1)
        sep.pack(fill="x", padx=16, pady=(12, 8))

        # -- Stats panel --
        ctk.CTkLabel(
            right, text="Estimation",
            font=(FONT_FAMILY, 14, "bold"), text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=16, pady=(4, 6))

        stats_frame = ctk.CTkFrame(right, fg_color=COLOR_INPUT_BG,
                                   corner_radius=8, border_width=1,
                                   border_color=COLOR_BORDER)
        stats_frame.pack(fill="x", padx=16, pady=(0, 10))

        self.stat_chars = self._make_stat_row(stats_frame, "Characters", "0")
        self.stat_words = self._make_stat_row(stats_frame, "Words", "0")
        self.stat_sentences = self._make_stat_row(stats_frame, "Sentences", "0")
        self.stat_est = self._make_stat_row(stats_frame, "Est. Time", "--")

        # -- Separator --
        ctk.CTkFrame(right, fg_color=COLOR_BORDER, height=1).pack(
            fill="x", padx=16, pady=(4, 8))

        # ====== DESIRED TIME CONTROL ======
        ctk.CTkLabel(
            right, text="Desired Time",
            font=(FONT_FAMILY, 14, "bold"), text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=16, pady=(4, 2))

        ctk.CTkLabel(
            right, text="Set a target and parameters auto-adjust",
            font=(FONT_FAMILY, 10), text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", padx=16, pady=(0, 6))

        # Mode toggle
        mode_frame = ctk.CTkFrame(right, fg_color="transparent")
        mode_frame.pack(fill="x", padx=16, pady=(0, 6))
        self.mode_var = tk.StringVar(value="auto")
        ctk.CTkRadioButton(
            mode_frame, text="Auto (time-driven)", variable=self.mode_var,
            value="auto", font=(FONT_FAMILY, 11), text_color=COLOR_TEXT_DIM,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self._on_mode_change,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(
            mode_frame, text="Manual", variable=self.mode_var,
            value="manual", font=(FONT_FAMILY, 11), text_color=COLOR_TEXT_DIM,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self._on_mode_change,
        ).pack(side="left")

        # Desired-time slider
        self.desired_time_var = tk.DoubleVar(value=0.0)
        dt_frame = ctk.CTkFrame(right, fg_color="transparent")
        dt_frame.pack(fill="x", padx=16, pady=(0, 4))
        dt_top = ctk.CTkFrame(dt_frame, fg_color="transparent")
        dt_top.pack(fill="x")
        ctk.CTkLabel(dt_top, text="Target",
                     font=(FONT_FAMILY, 12), text_color=COLOR_TEXT_DIM
                     ).pack(side="left")
        self.desired_time_label = ctk.CTkLabel(
            dt_top, text="--",
            font=(FONT_FAMILY, 12, "bold"), text_color=COLOR_TEXT)
        self.desired_time_label.pack(side="right")

        self.desired_slider = ctk.CTkSlider(
            dt_frame, from_=0, to=600, variable=self.desired_time_var,
            width=200, height=16, corner_radius=8,
            fg_color=COLOR_INPUT_BG, progress_color=COLOR_GREEN,
            button_color=COLOR_GREEN, button_hover_color=COLOR_ACCENT_HOVER,
        )
        self.desired_slider.pack(fill="x", pady=(2, 0))
        self.desired_time_var.trace_add("write", self._on_desired_time_slider)

        # Custom entry row
        custom_frame = ctk.CTkFrame(right, fg_color="transparent")
        custom_frame.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(custom_frame, text="Custom (min):",
                     font=(FONT_FAMILY, 11), text_color=COLOR_TEXT_DIM
                     ).pack(side="left")
        self.custom_time_entry = ctk.CTkEntry(
            custom_frame, width=70, height=28, font=(FONT_FAMILY, 12),
            fg_color=COLOR_INPUT_BG, text_color=COLOR_TEXT,
            border_color=COLOR_BORDER, corner_radius=6,
            placeholder_text="min")
        self.custom_time_entry.pack(side="left", padx=(6, 6))
        ctk.CTkButton(
            custom_frame, text="Set", width=50, height=28,
            font=(FONT_FAMILY, 11), corner_radius=6,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self._on_custom_time_set,
        ).pack(side="left")

        # Warning label
        self.time_warning = ctk.CTkLabel(
            right, text="",
            font=(FONT_FAMILY, 10), text_color=COLOR_YELLOW,
            wraplength=260,
        )
        self.time_warning.pack(anchor="w", padx=16, pady=(2, 10))

        # ====== BOTTOM BAR — Controls & Progress ======
        bottom = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=0, height=110)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        ctrl = ctk.CTkFrame(bottom, fg_color="transparent")
        ctrl.pack(fill="x", padx=20, pady=(12, 4))

        self.start_btn = ctk.CTkButton(
            ctrl, text="Start Typing", width=150, height=40,
            font=(FONT_FAMILY, 14, "bold"), corner_radius=10,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self._start,
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = ctk.CTkButton(
            ctrl, text="Stop", width=100, height=40,
            font=(FONT_FAMILY, 14, "bold"), corner_radius=10,
            fg_color=COLOR_RED, hover_color=COLOR_RED_HOVER,
            state="disabled", command=self._stop,
        )
        self.stop_btn.pack(side="left", padx=(0, 20))

        self.status_label = ctk.CTkLabel(
            ctrl, text="Ready  --  Paste text and adjust settings",
            font=(FONT_FAMILY, 12), text_color=COLOR_TEXT_DIM,
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.elapsed_label = ctk.CTkLabel(
            ctrl, text="",
            font=(FONT_FAMILY, 12), text_color=COLOR_GREEN,
        )
        self.elapsed_label.pack(side="right")

        prog_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        prog_frame.pack(fill="x", padx=20, pady=(2, 14))

        self.progress = ctk.CTkProgressBar(
            prog_frame, height=10, corner_radius=5,
            fg_color=COLOR_INPUT_BG, progress_color=COLOR_ACCENT,
        )
        self.progress.pack(fill="x")
        self.progress.set(0)

    # ------------------------------------------------------------------
    # Slider factory
    # ------------------------------------------------------------------
    def _make_slider(self, parent, label, var, from_, to, suffix,
                     resolution=1):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=16, pady=(0, 8))

        top_row = ctk.CTkFrame(frame, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(
            top_row, text=label,
            font=(FONT_FAMILY, 12), text_color=COLOR_TEXT_DIM,
        ).pack(side="left")

        val_label = ctk.CTkLabel(
            top_row, text=self._fmt_val(var.get(), suffix),
            font=(FONT_FAMILY, 12, "bold"), text_color=COLOR_TEXT,
        )
        val_label.pack(side="right")

        slider = ctk.CTkSlider(
            frame, from_=from_, to=to, variable=var,
            width=200, height=16, corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER,
        )
        slider.pack(fill="x", pady=(2, 0))

        def _on_change(*_):
            if self._suppressing_trace:
                return
            raw = var.get()
            if resolution >= 1:
                snapped = round(raw / resolution) * resolution
                snapped = int(snapped)
            else:
                snapped = round(raw / resolution) * resolution
                snapped = round(snapped, 3)
            self._suppressing_trace = True
            var.set(snapped)
            self._suppressing_trace = False
            val_label.configure(text=self._fmt_val(snapped, suffix))
            # If user moves a manual slider, switch to manual mode
            if self._auto_mode and not self._suppressing_trace:
                self._auto_mode = False
                self.mode_var.set("manual")
            self._update_stats()

        var.trace_add("write", _on_change)

    @staticmethod
    def _fmt_val(v, suffix):
        if isinstance(v, float):
            return f"{v:.1f} {suffix}"
        return f"{v} {suffix}"

    # ------------------------------------------------------------------
    # Stat rows
    # ------------------------------------------------------------------
    def _make_stat_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(
            row, text=label,
            font=(FONT_FAMILY, 12), text_color=COLOR_TEXT_DIM,
        ).pack(side="left")
        val = ctk.CTkLabel(
            row, text=value,
            font=(FONT_FAMILY, 12, "bold"), text_color=COLOR_TEXT,
        )
        val.pack(side="right")
        return val

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _load_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt *.md *.doc"),
                       ("All files", "*.*")])
        if path:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            self.text_box.delete("1.0", "end")
            self.text_box.insert("1.0", content)
            self._update_stats()

    def _paste_clipboard(self):
        try:
            content = self.clipboard_get()
            if content:
                self.text_box.delete("1.0", "end")
                self.text_box.insert("1.0", content)
                self._update_stats()
        except tk.TclError:
            pass

    def _clear_text(self):
        self.text_box.delete("1.0", "end")
        self._update_stats()

    def _get_text(self) -> str:
        return self.text_box.get("1.0", "end").rstrip('\n')

    def _build_profile(self) -> TypingProfile:
        p = TypingProfile()
        p.speed_multiplier = self.speed_var.get()
        p.base_wpm = self.wpm_var.get()
        p.error_rate = self.error_var.get() / 100.0
        p.thinking_probability = self.thinking_var.get() / 100.0
        p.distraction_probability = self.distraction_var.get() / 100.0
        p.save_pause_interval = max(10, int(self.save_var.get()))
        p.countdown_seconds = int(self.countdown_var.get())
        return p

    def _on_mode_change(self):
        self._auto_mode = (self.mode_var.get() == "auto")
        if self._auto_mode:
            self._on_desired_time_change()

    def _on_desired_time_slider(self, *_):
        if self._suppressing_trace:
            return
        secs = self.desired_time_var.get()
        self.desired_time_label.configure(text=format_duration(secs))
        if self._auto_mode:
            self._on_desired_time_change()

    def _on_custom_time_set(self):
        try:
            mins = float(self.custom_time_entry.get())
            secs = mins * 60.0
            secs = max(self._min_time_seconds, secs)
            self._suppressing_trace = True
            self.desired_time_var.set(secs)
            self._suppressing_trace = False
            self.desired_time_label.configure(text=format_duration(secs))
            self._auto_mode = True
            self.mode_var.set("auto")
            self._on_desired_time_change()
        except ValueError:
            pass

    def _on_desired_time_change(self):
        """Solve parameters to match the desired time and push to sliders."""
        text = self._get_text()
        if not text.strip():
            return
        target = self.desired_time_var.get()
        if target <= 0:
            return

        # Build a base profile preserving error/save/countdown from current
        base = self._build_profile()
        solved = solve_profile_for_time(text, target, base)

        # Push solved values into sliders without triggering manual-mode switch
        self._suppressing_trace = True
        self.speed_var.set(round(solved.speed_multiplier, 1))
        self.wpm_var.set(round(solved.base_wpm / 5) * 5)
        self.thinking_var.set(round(solved.thinking_probability * 100, 1))
        self.distraction_var.set(round(solved.distraction_probability * 100, 2))
        self._suppressing_trace = False

        # Show warning if below default estimate
        if target < self._default_est_seconds:
            self.time_warning.configure(
                text="Below recommended time -- may look less natural",
                text_color=COLOR_YELLOW)
        elif target < self._min_time_seconds * 1.5:
            self.time_warning.configure(
                text="Near minimum -- very fast typing",
                text_color=COLOR_RED)
        else:
            self.time_warning.configure(text="")

        self._update_stats()

    def _update_stats(self):
        text = self._get_text()
        if not text.strip():
            self.stat_chars.configure(text="0")
            self.stat_words.configure(text="0")
            self.stat_sentences.configure(text="0")
            self.stat_est.configure(text="--")
            self.desired_time_label.configure(text="--")
            self.time_warning.configure(text="")
            return
        chars = len(text)
        words = len(text.split())
        sents = text.count('.') + text.count('!') + text.count('?')
        profile = self._build_profile()
        est = estimate_time(text, profile)
        self.stat_chars.configure(text=f"{chars:,}")
        self.stat_words.configure(text=f"{words:,}")
        self.stat_sentences.configure(text=f"{sents:,}")
        self.stat_est.configure(text=format_duration(est))

        # Recompute default estimate and min time for slider bounds
        default_p = TypingProfile()
        self._default_est_seconds = estimate_time(text, default_p)
        self._min_time_seconds = compute_minimum_time(text)

        # Update desired-time slider range: min .. default + 2 hours
        max_time = self._default_est_seconds + 7200
        self._suppressing_trace = True
        self.desired_slider.configure(from_=self._min_time_seconds, to=max_time)
        # If desired time hasn't been set yet, initialize to default
        if self.desired_time_var.get() < self._min_time_seconds:
            self.desired_time_var.set(self._default_est_seconds)
            self.desired_time_label.configure(
                text=format_duration(self._default_est_seconds))
        self._suppressing_trace = False

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------
    def _start(self):
        text = self._get_text()
        if not text.strip():
            self.status_label.configure(text="No text to type!", text_color=COLOR_RED)
            return

        self._is_running = True
        self._stop_flag = False
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.set(0)

        profile = self._build_profile()
        countdown_sec = profile.countdown_seconds

        # Countdown in a thread so the UI stays responsive
        self._typing_thread = threading.Thread(
            target=self._run_typing, args=(text, profile, countdown_sec),
            daemon=True
        )
        self._typing_thread.start()

    def _stop(self):
        self._stop_flag = True
        self.status_label.configure(
            text="Stopping...", text_color=COLOR_RED
        )

    def _run_typing(self, text, profile, countdown_sec):
        # --- Countdown ---
        for i in range(countdown_sec, 0, -1):
            if self._stop_flag:
                self._finish("Aborted during countdown")
                return
            self.after(0, lambda s=i: self.status_label.configure(
                text=f"Place cursor in Google Docs!  Starting in {s}...",
                text_color="#f0c040"
            ))
            import time
            time.sleep(1)

        self.after(0, lambda: self.status_label.configure(
            text="Typing...", text_color=COLOR_GREEN
        ))

        # --- Type ---
        def on_progress(done, total, elapsed):
            if total > 0:
                pct = done / total
                self.after(0, lambda p=pct, e=elapsed: self._update_progress(p, e))

        chars, elapsed = type_text(
            text, profile,
            on_progress=on_progress,
            should_stop=lambda: self._stop_flag,
        )

        if self._stop_flag:
            self._finish(f"Stopped after {chars:,} chars  ({format_duration(elapsed)})")
        else:
            self._finish(f"Done!  {chars:,} chars in {format_duration(elapsed)}")

    def _update_progress(self, pct, elapsed):
        self.progress.set(pct)
        self.elapsed_label.configure(text=format_duration(elapsed))

    def _finish(self, msg):
        self._is_running = False
        self.after(0, lambda: [
            self.start_btn.configure(state="normal"),
            self.stop_btn.configure(state="disabled"),
            self.status_label.configure(text=msg, text_color=COLOR_TEXT),
            self.progress.set(1.0 if "Done" in msg else self.progress.get()),
        ])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = TypeflowApp()
    app.mainloop()
