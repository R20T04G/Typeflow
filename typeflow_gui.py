"""
Typeflow GUI v2 — Simplified interface with advanced options toggle.

Default view: text input + desired time slider + start/stop.
Advanced: all parameter sliders exposed.
"""

import os
import sys
import threading
import tkinter as tk
import time
from tkinter import filedialog

import customtkinter as ctk

if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _base)

from typeflow_engine import (
    TypingProfile, estimate_time, format_duration, type_text,
    compute_minimum_time, solve_profile_for_time,
)
from ai_cleanup import scan as ai_scan, clean as ai_clean

# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------
def load_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return '\n'.join(p.text for p in doc.paragraphs)

def load_pdf(path: str) -> str:
    import fitz
    doc = fitz.open(path)
    parts = []
    for page in doc:
        parts.append(page.get_text())
    doc.close()
    return '\n'.join(parts)

def load_text_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        return load_docx(path)
    elif ext == '.pdf':
        return load_pdf(path)
    else:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT = "Segoe UI"
BG = "#0f0f14"
CARD = "#1a1a24"
ACCENT = "#6c5ce7"
ACCENT_H = "#7e6ff0"
RED = "#e74c3c"
RED_H = "#ff6b5a"
GREEN = "#00b894"
YELLOW = "#f0c040"
TEXT = "#e8e8f0"
DIM = "#8888a0"
BORDER = "#2a2a3a"
INPUT = "#12121c"


class TypeflowApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Typeflow")
        self.geometry("940x680")
        self.minsize(800, 560)
        self.configure(fg_color=BG)

        try:
            self.iconbitmap(os.path.join(_base, "icon.ico"))
        except Exception:
            pass

        self._stop_flag = False
        self._pause_flag = False
        self._is_running = False
        self._cursor_index = 0
        self._cursor_tag = "typing_cursor"
        self._cursor_fps_limit = 30.0
        self._last_cursor_draw = 0.0
        self._active_profile = None
        self._text_changed_during_run = False
        self._text_change_pause_latched = False
        self._resume_delay_seconds = 5
        self._resume_deadline = 0.0
        self._resume_last_second = None
        self._suppress = False
        self._auto_mode = True
        self._default_est = 0.0
        self._min_time = 0.0
        self._typing_thread = None
        self._slider_labels = {}  # id(var) -> (label_widget, suffix)
        self._refresh_timer = None  # debounce timer id

        self._build()
        self.after(500, self._show_tutorial)

    # ==================================================================
    # BUILD UI
    # ==================================================================
    def _build(self):
        # --- Top bar ---
        top = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=50)
        top.pack(fill="x")
        top.pack_propagate(False)
        ctk.CTkLabel(top, text="TYPEFLOW", font=(FONT, 18, "bold"),
                     text_color=ACCENT).pack(side="left", padx=16)
        ctk.CTkLabel(top, text="Human-like typing simulator",
                     font=(FONT, 11), text_color=DIM).pack(side="left")
        ctk.CTkLabel(top, text="Use Pause/Stop buttons while typing",
                 font=(FONT, 10), text_color=DIM).pack(side="right", padx=16)

        # --- Body: two columns ---
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # ========== LEFT: Text input ==========
        left = ctk.CTkFrame(body, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(hdr, text="Text to Type", font=(FONT, 13, "bold"),
                     text_color=TEXT).pack(side="left")

        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.pack(side="right")
        for label, cmd in [("Load File", self._load_file),
                           ("Paste", self._paste), ("Clear", self._clear)]:
            ctk.CTkButton(btns, text=label, width=75, height=28,
                          font=(FONT, 11), corner_radius=6,
                          fg_color=BORDER, hover_color="#2e2e3e",
                          command=cmd).pack(side="left", padx=2)

        self.text_box = ctk.CTkTextbox(left, font=(FONT, 12), corner_radius=8,
                                       fg_color=INPUT, text_color=TEXT,
                                       border_width=1, border_color=BORDER,
                                       wrap="word")
        self.text_box.pack(fill="both", expand=True, padx=14, pady=(4, 6))
        tk_text = getattr(self.text_box, "_textbox", self.text_box)
        tk_text.configure(insertwidth=0)
        tk_text.tag_configure(self._cursor_tag, background=YELLOW, foreground="#000000")
        self.text_box.bind("<KeyRelease>", self._on_text_key_release)
        self.text_box.bind("<KeyPress>", self._on_text_key_press)
        self.text_box.bind("<ButtonRelease-1>", self._on_cursor_moved)
        self.text_box.bind("<ButtonRelease-3>", self._on_cursor_moved)

        # AI cleanup bar (hidden by default)
        self.ai_bar = ctk.CTkFrame(left, fg_color="#1e1428", corner_radius=8,
                                   border_width=1, border_color="#3a2a5a")
        # Not packed yet — shown only when artifacts detected
        self.ai_label = ctk.CTkLabel(self.ai_bar, text="", font=(FONT, 11),
                                     text_color=YELLOW)
        self.ai_label.pack(side="left", padx=12, pady=6)
        ctk.CTkButton(self.ai_bar, text="Clean", width=60, height=26,
                      font=(FONT, 11), corner_radius=6,
                      fg_color=ACCENT, hover_color=ACCENT_H,
                      command=self._do_ai_cleanup).pack(side="right", padx=12, pady=6)

        # ========== RIGHT: Controls ==========
        right = ctk.CTkScrollableFrame(body, fg_color=CARD, corner_radius=12,
                                       border_width=1, border_color=BORDER,
                                       scrollbar_button_color=BORDER,
                                       scrollbar_button_hover_color=ACCENT)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # --- Stats ---
        ctk.CTkLabel(right, text="Summary", font=(FONT, 13, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 6))
        sf = ctk.CTkFrame(right, fg_color=INPUT, corner_radius=8,
                          border_width=1, border_color=BORDER)
        sf.pack(fill="x", padx=14, pady=(0, 8))
        self.stat_chars = self._stat(sf, "Characters", "0")
        self.stat_words = self._stat(sf, "Words", "0")
        self.stat_est = self._stat(sf, "Est. Time", "--")

        # --- Desired time ---
        ctk.CTkFrame(right, fg_color=BORDER, height=1).pack(fill="x", padx=14, pady=6)
        ctk.CTkLabel(right, text="Desired Time", font=(FONT, 13, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=14, pady=(4, 2))
        ctk.CTkLabel(right, text="Drag to choose how long the typing takes",
                     font=(FONT, 10), text_color=DIM).pack(anchor="w", padx=14)

        self.desired_var = tk.DoubleVar(value=0)
        dt = ctk.CTkFrame(right, fg_color="transparent")
        dt.pack(fill="x", padx=14, pady=(6, 2))
        ctk.CTkLabel(dt, text="Target", font=(FONT, 11),
                     text_color=DIM).pack(side="left")
        self.desired_label = ctk.CTkLabel(dt, text="--", font=(FONT, 11, "bold"),
                                          text_color=TEXT)
        self.desired_label.pack(side="right")

        self.desired_slider = ctk.CTkSlider(
            right, from_=0, to=600, variable=self.desired_var,
            height=14, corner_radius=7, fg_color=INPUT,
            progress_color=GREEN, button_color=GREEN,
            button_hover_color=ACCENT_H)
        self.desired_slider.pack(fill="x", padx=14, pady=(0, 2))
        self.desired_var.trace_add("write", self._on_desired_change)

        # Custom time entry
        cf = ctk.CTkFrame(right, fg_color="transparent")
        cf.pack(fill="x", padx=14, pady=(2, 6))
        ctk.CTkLabel(cf, text="Custom (min):", font=(FONT, 10),
                     text_color=DIM).pack(side="left")
        self.custom_entry = ctk.CTkEntry(cf, width=65, height=26,
                                         font=(FONT, 11), fg_color=INPUT,
                                         text_color=TEXT, border_color=BORDER,
                                         corner_radius=5, placeholder_text="min")
        self.custom_entry.pack(side="left", padx=4)
        ctk.CTkButton(cf, text="Set", width=44, height=26, font=(FONT, 10),
                      corner_radius=5, fg_color=ACCENT, hover_color=ACCENT_H,
                      command=self._set_custom_time).pack(side="left")

        # Warning
        self.time_warn = ctk.CTkLabel(right, text="", font=(FONT, 10),
                                      text_color=YELLOW, wraplength=240)
        self.time_warn.pack(anchor="w", padx=14, pady=(0, 4))

        # --- Advanced toggle ---
        ctk.CTkFrame(right, fg_color=BORDER, height=1).pack(fill="x", padx=14, pady=6)
        self.adv_open = False
        f_adv = ctk.CTkFrame(right, fg_color="transparent")
        f_adv.pack(fill="x")
        self.adv_btn = ctk.CTkButton(
            f_adv, text="Advanced Settings  +", width=200, height=30,
            font=(FONT, 12), corner_radius=8,
            fg_color="transparent", hover_color="#22222e",
            text_color=DIM, command=self._toggle_advanced)
        self.adv_btn.pack(side="left", padx=14, pady=(0, 4))
        self.reset_btn = ctk.CTkButton(
            f_adv, text="Reset to Default", width=120, height=30,
            font=(FONT, 12), corner_radius=8,
            fg_color="transparent", hover_color="#22222e",
            text_color=DIM, command=self._reset_params)
        self.reset_btn.pack(side="left", padx=4, pady=(0, 4))

        self.adv_frame = ctk.CTkFrame(right, fg_color="transparent")
        # NOT packed — hidden by default

        # Build advanced sliders inside adv_frame
        self.speed_var = tk.DoubleVar(value=1.0)
        self._slider(self.adv_frame, "Speed Multiplier", self.speed_var,
                     0.3, 3.0, "x", 0.1)
        self.wpm_var = tk.DoubleVar(value=55.0)
        self.error_var = tk.DoubleVar(value=2.0)
        self._slider(self.adv_frame, "Typo Rate", self.error_var, 0, 8, "%", 0.1)
        self.think_var = tk.DoubleVar(value=0.6)
        self._slider(self.adv_frame, "Thinking Pauses", self.think_var,
                     0, 5, "%", 0.1)
        self.distract_var = tk.DoubleVar(value=0.08)
        self._slider(self.adv_frame, "Distraction Breaks", self.distract_var,
                     0, 2, "%", 0.02)
        self.save_var = tk.IntVar(value=300)
        self._slider(self.adv_frame, "Save Pause Interval", self.save_var,
                     50, 1000, "chars", 50)
        self.cd_var = tk.IntVar(value=5)
        self._slider(self.adv_frame, "Countdown", self.cd_var, 3, 15, "sec", 1)

        # Mode radio
        mode_f = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        mode_f.pack(fill="x", padx=4, pady=(8, 4))
        self.mode_var = tk.StringVar(value="auto")
        ctk.CTkRadioButton(mode_f, text="Auto", variable=self.mode_var,
                           value="auto", font=(FONT, 11), text_color=DIM,
                           fg_color=ACCENT, command=self._mode_changed
                           ).pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(mode_f, text="Manual", variable=self.mode_var,
                           value="manual", font=(FONT, 11), text_color=DIM,
                           fg_color=ACCENT, command=self._mode_changed
                           ).pack(side="left")

        # ========== BOTTOM BAR ==========
        bot = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=100)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)

        ctrl = ctk.CTkFrame(bot, fg_color="transparent")
        ctrl.pack(fill="x", padx=16, pady=(10, 2))

        self.start_btn = ctk.CTkButton(
            ctrl, text="Start Typing", width=140, height=38,
            font=(FONT, 13, "bold"), corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_H, command=self._start)
        self.start_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            ctrl, text="Stop", width=90, height=38,
            font=(FONT, 13, "bold"), corner_radius=10,
            fg_color=RED, hover_color=RED_H,
            state="disabled", command=self._stop)
        self.stop_btn.pack(side="left", padx=(0, 4))

        self.pause_btn = ctk.CTkButton(
            ctrl, text="Pause", width=90, height=38,
            font=(FONT, 13, "bold"), corner_radius=10,
            fg_color=BORDER, hover_color="#2e2e3e",
            text_color=TEXT,
            state="disabled", command=self._toggle_pause)
        self.pause_btn.pack(side="left", padx=(0, 16))

        self.status = ctk.CTkLabel(ctrl, text="Ready -- load or paste text",
                                   font=(FONT, 11), text_color=DIM)
        self.status.pack(side="left", fill="x", expand=True)

        self.elapsed = ctk.CTkLabel(ctrl, text="", font=(FONT, 11),
                                    text_color=GREEN)
        self.elapsed.pack(side="right")

        pf = ctk.CTkFrame(bot, fg_color="transparent")
        pf.pack(fill="x", padx=16, pady=(2, 12))
        self.progress = ctk.CTkProgressBar(pf, height=8, corner_radius=4,
                                           fg_color=INPUT, progress_color=ACCENT)
        self.progress.pack(fill="x")
        self.progress.set(0)
        self._sync_visual_cursor()

    # ==================================================================
    # SLIDER FACTORY
    # ==================================================================
    def _slider(self, parent, label, var, lo, hi, suffix, res):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=4, pady=(0, 6))
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text=label, font=(FONT, 11),
                     text_color=DIM).pack(side="left")
        vl = ctk.CTkLabel(row, text=self._fv(var.get(), suffix),
                          font=(FONT, 11, "bold"), text_color=TEXT)
        vl.pack(side="right")
        ctk.CTkSlider(f, from_=lo, to=hi, variable=var,
                      height=14, corner_radius=7, fg_color=INPUT,
                      progress_color=ACCENT, button_color=ACCENT,
                      button_hover_color=ACCENT_H).pack(fill="x", pady=(2, 0))

        def _chg(*_):
            if self._suppress:
                return
            raw = var.get()
            if res >= 1:
                s = int(round(raw / res) * res)
            else:
                s = round(round(raw / res) * res, 3)
            self._suppress = True
            var.set(s)
            self._suppress = False
            vl.configure(text=self._fv(s, suffix))
            if self._auto_mode:
                self._auto_mode = False
                self.mode_var.set("manual")
            self._refresh()
        var.trace_add("write", _chg)
        self._slider_labels[id(var)] = (vl, suffix)

    @staticmethod
    def _fv(v, s):
        return f"{v:.1f} {s}" if isinstance(v, float) else f"{v} {s}"

    def _stat(self, parent, label, val):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(r, text=label, font=(FONT, 11), text_color=DIM).pack(side="left")
        v = ctk.CTkLabel(r, text=val, font=(FONT, 11, "bold"), text_color=TEXT)
        v.pack(side="right")
        return v

    # ==================================================================
    # ADVANCED TOGGLE
    # ==================================================================
    def _toggle_advanced(self):
        self.adv_open = not self.adv_open
        if self.adv_open:
            self.adv_frame.pack(fill="x", padx=14, pady=(0, 8))
            self.adv_btn.configure(text="Advanced Settings  -")
        else:
            self.adv_frame.pack_forget()
            self.adv_btn.configure(text="Advanced Settings  +")

    # ==================================================================
    # ACTIONS
    # ==================================================================
    def _load_file(self):
        path = filedialog.askopenfilename(filetypes=[
            ("All supported", "*.txt *.md *.docx *.pdf"),
            ("Text files", "*.txt *.md"),
            ("Word documents", "*.docx"),
            ("PDF files", "*.pdf"),
            ("All files", "*.*"),
        ])
        if path:
            try:
                content = load_text_file(path)
                self.text_box.delete("1.0", "end")
                self.text_box.insert("1.0", content)
                self._tk_text().mark_set("insert", "1.0")
                self._set_cursor_index(0, see=True, force=True)
                self._refresh()
            except Exception as e:
                self.status.configure(
                    text=f"Error loading file: {e}", text_color=RED)

    def _paste(self):
        try:
            c = self.clipboard_get()
            if c:
                self.text_box.delete("1.0", "end")
                self.text_box.insert("1.0", c)
                self._tk_text().mark_set("insert", "1.0")
                self._set_cursor_index(0, see=True, force=True)
                self._refresh()
        except tk.TclError:
            pass

    def _clear(self):
        self.text_box.delete("1.0", "end")
        self._tk_text().mark_set("insert", "1.0")
        self._set_cursor_index(0, force=True)
        self.ai_bar.pack_forget()
        self._refresh()

    def _txt(self) -> str:
        return self.text_box.get("1.0", "end-1c")

    def _tk_text(self):
        return getattr(self.text_box, "_textbox", self.text_box)

    def _sync_visual_cursor(self, see=False):
        tk_text = self._tk_text()
        text = self._txt()
        tk_text.tag_remove(self._cursor_tag, "1.0", "end")
        if not text:
            return

        max_index = len(text) - 1
        self._cursor_index = max(0, min(self._cursor_index, max_index))
        start = f"1.0 + {self._cursor_index} chars"
        end = f"{start} + 1 chars"
        tk_text.tag_add(self._cursor_tag, start, end)
        if see:
            tk_text.see(start)

    def _set_cursor_index(self, index, see=False, force=False):
        self._cursor_index = max(0, int(index))
        now = time.perf_counter()
        if not force and (now - self._last_cursor_draw) < (1.0 / self._cursor_fps_limit):
            return
        self._sync_visual_cursor(see=see)
        self._last_cursor_draw = now

    def _on_text_key_press(self, _event=None):
        if self._is_running:
            return "break"

    def _on_text_key_release(self, _event=None):
        self._update_cursor_index()
        self._sync_visual_cursor(see=True)
        self._debounced_refresh()

    def _on_cursor_moved(self, _event=None):
        self._update_cursor_index()
        self._sync_visual_cursor(see=True)

    def _update_cursor_index(self):
        try:
            self._cursor_index = len(self._tk_text().get("1.0", "insert"))
        except tk.TclError:
            self._cursor_index = 0

    def _get_text_and_cursor(self):
        text = self._txt()
        self._update_cursor_index()
        cursor = max(0, min(self._cursor_index, len(text)))
        return text, cursor

    # ==================================================================
    # AI CLEANUP
    # ==================================================================
    def _check_ai(self):
        text = self._txt()
        if not text.strip():
            self.ai_bar.pack_forget()
            return
        hits = ai_scan(text)
        if hits:
            total = sum(h["count"] for h in hits)
            names = ", ".join(h["description"] for h in hits[:3])
            more = f" +{len(hits)-3} more" if len(hits) > 3 else ""
            self.ai_label.configure(
                text=f"{total} AI artifacts found: {names}{more}")
            self.ai_bar.pack(fill="x", padx=14, pady=(0, 10))
        else:
            self.ai_bar.pack_forget()

    def _do_ai_cleanup(self):
        text = self._txt()
        cleaned = ai_clean(text, selected_names=None)
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", cleaned)
        self._set_cursor_index(0, see=True, force=True)
        self.ai_bar.pack_forget()
        self._refresh()
        self.status.configure(text="AI artifacts cleaned", text_color=GREEN)

    # ==================================================================
    # PROFILE
    # ==================================================================
    def _profile(self) -> TypingProfile:
        p = TypingProfile()
        p.speed_multiplier = self.speed_var.get()
        p.base_wpm = self.wpm_var.get()
        p.error_rate = self.error_var.get() / 100.0
        p.thinking_probability = self.think_var.get() / 100.0
        p.distraction_probability = self.distract_var.get() / 100.0
        p.save_pause_interval = max(10, int(self.save_var.get()))
        p.countdown_seconds = int(self.cd_var.get())
        return p

    # ==================================================================
    # DESIRED TIME
    # ==================================================================
    def _on_desired_change(self, *_):
        if self._suppress:
            return
        secs = self.desired_var.get()
        self.desired_label.configure(text=format_duration(secs))
        if self._auto_mode:
            self._solve_for_time()

    def _set_custom_time(self):
        try:
            mins = float(self.custom_entry.get())
            secs = max(self._min_time, mins * 60.0)
            self._suppress = True
            self.desired_var.set(secs)
            self._suppress = False
            self.desired_label.configure(text=format_duration(secs))
            self._auto_mode = True
            self.mode_var.set("auto")
            self._solve_for_time()
        except ValueError:
            pass

    def _mode_changed(self):
        self._auto_mode = (self.mode_var.get() == "auto")
        if self._auto_mode:
            self._solve_for_time()

    def _solve_for_time(self):
        text = self._txt()
        if not text.strip():
            return
        target = self.desired_var.get()
        if target <= 0:
            return
        base = self._profile()
        solved = solve_profile_for_time(text, target, base)
        self._suppress = True
        self.speed_var.set(round(solved.speed_multiplier, 1))
        self.wpm_var.set(round(solved.base_wpm / 2) * 2)
        self.think_var.set(round(solved.thinking_probability * 100, 1))
        self.distract_var.set(round(solved.distraction_probability * 100, 2))
        self._suppress = False

        # Update slider value labels (since _suppress blocked _chg callbacks)
        self._update_slider_labels()

        # Warning — check severe first, then mild
        if self._min_time > 0 and target < self._min_time * 1.5:
            self.time_warn.configure(text="Near minimum -- very fast",
                                     text_color=RED)
        elif self._default_est > 0 and target < self._default_est:
            self.time_warn.configure(
                text="Below recommended -- may look less natural",
                text_color=YELLOW)
        else:
            self.time_warn.configure(text="")

        # Update est label directly (no _refresh to avoid loops)
        p = self._profile()
        est = estimate_time(text, p)
        self.stat_est.configure(text=format_duration(est))

    def _update_slider_labels(self):
        """Sync all slider value labels with their current var values."""
        for var in [self.speed_var, self.wpm_var, self.error_var,
                    self.think_var, self.distract_var, self.save_var, self.cd_var]:
            key = id(var)
            if key in self._slider_labels:
                lbl, suffix = self._slider_labels[key]
                lbl.configure(text=self._fv(var.get(), suffix))

    # ==================================================================
    # REFRESH STATS
    # ==================================================================
    def _debounced_refresh(self):
        """Debounce text changes: wait 300ms after last keystroke."""
        if self._refresh_timer is not None:
            self.after_cancel(self._refresh_timer)
        self._refresh_timer = self.after(300, self._refresh)

    def _refresh(self):
        self._refresh_timer = None
        text = self._txt()
        if not text.strip():
            self.stat_chars.configure(text="0")
            self.stat_words.configure(text="0")
            self.stat_est.configure(text="--")
            self.desired_label.configure(text="--")
            self.time_warn.configure(text="")
            self._sync_visual_cursor()
            return

        chars = len(text)
        words = len(text.split())
        p = self._profile()
        est = estimate_time(text, p)
        self.stat_chars.configure(text=f"{chars:,}")
        self.stat_words.configure(text=f"{words:,}")
        self.stat_est.configure(text=format_duration(est))

        default_p = TypingProfile()
        self._default_est = estimate_time(text, default_p)
        self._min_time = compute_minimum_time(text)

        max_t = self._default_est + 7200
        self._suppress = True
        self.desired_slider.configure(from_=self._min_time, to=max_t)
        need_init = self.desired_var.get() < self._min_time
        if need_init:
            self.desired_var.set(self._default_est)
            self.desired_label.configure(text=format_duration(self._default_est))
        self._suppress = False

        # If we just initialized the desired time and auto mode, solve now
        if need_init and self._auto_mode:
            self._solve_for_time()

        # Check for AI artifacts
        self._check_ai()
        self._sync_visual_cursor()

    # ==================================================================
    # START / STOP
    # ==================================================================
    def _start(self):
        text, start_index = self._get_text_and_cursor()
        if not text.strip():
            self.status.configure(text="No text to type!", text_color=RED)
            return
        if start_index >= len(text):
            self.status.configure(
                text="Cursor is at the end. Move it earlier in the text box to start typing.",
                text_color=YELLOW)
            return
        self._is_running = True
        self._stop_flag = False
        self._pause_flag = False
        self._text_change_pause_latched = False
        self._active_text_snapshot = text
        self._last_text_check = 0.0
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.pause_btn.configure(state="normal", text="Pause")
        self.focus_set()
        self.progress.set(0)
        profile = self._profile()
        self._typing_thread = threading.Thread(
            target=self._run,
            args=(text, start_index, profile, profile.countdown_seconds),
            daemon=True)
        self._typing_thread.start()


    def _toggle_pause(self):
        if self._pause_flag:
            self.pause_btn.configure(state="disabled")
            threading.Thread(target=self._resume_countdown, daemon=True).start()
        else:
            self._set_pause_state(True)

    def _resume_countdown(self):
        import time as _t
        cd = int(self.cd_var.get())
        for i in range(cd, 0, -1):
            if self._stop_flag:
                return
            self.after(0, lambda s=i: self.status.configure(
                text=f"Resuming in {s}... Switch to your document!",
                text_color=YELLOW))
            _t.sleep(1)
        self.after(0, lambda: self._set_pause_state(False))
        self.after(0, lambda: self.pause_btn.configure(state="normal"))

    def _set_pause_state(self, paused, reason=None):
        self._pause_flag = paused
        self.pause_btn.configure(text="Resume" if paused else "Pause")
        if not self._is_running:
            return
        if paused:
            msg = "Paused..."
            if reason:
                msg = f"Paused ({reason})"
            self.status.configure(text=msg, text_color=YELLOW)
        else:
            self._text_change_pause_latched = False
            self.status.configure(text="Typing...", text_color=GREEN)

    def _reset_params(self):
        self._suppress = True
        self.speed_var.set(1.0)
        self.wpm_var.set(55.0)
        self.error_var.set(2.0)
        self.think_var.set(0.6)
        self.distract_var.set(0.08)
        self.save_var.set(300)
        self.cd_var.set(5)
        self._suppress = False
        self._auto_mode = True
        self.mode_var.set("auto")
        self._update_slider_labels()
        self._refresh()
        if self._txt().strip():
            self._solve_for_time()
        self.status.configure(text="Parameters reset to default values", text_color=GREEN)

    def _stop(self):
        self._stop_flag = True
        self.status.configure(text="Stopping...", text_color=RED)

    def _run(self, text, start_index, profile, cd):
        import time as _t

        for i in range(cd, 0, -1):
            if self._stop_flag:
                self._done("Aborted")
                return
            self.after(0, lambda s=i: self.status.configure(
                text=f"Switch to your document now!  {s}...",
                text_color=YELLOW))
            _t.sleep(1)

        self.after(0, lambda: self.status.configure(
            text="Typing...", text_color=GREEN))

        def prog(done, total, el):
            if total > 0:
                self.after(0, lambda p=done/total, e=el: [
                    self.progress.set(p),
                    self.elapsed.configure(text=format_duration(e)),
                    self._set_cursor_index(done, see=True)])

        def check_pause_logic():
            now = time.perf_counter()
            if (now - self._last_text_check) >= 0.1:
                self._last_text_check = now
                current_text = self._txt()
                if current_text != self._active_text_snapshot:
                    self._active_text_snapshot = current_text
                    if not self._pause_flag and not self._text_change_pause_latched:
                        self._text_change_pause_latched = True
                        self.after(0, lambda: self._set_pause_state(True, "text box changed"))

            return self._pause_flag

        try:
            chars, el = type_text(text, profile,
                                  on_progress=prog,
                                  should_stop=lambda: self._stop_flag,
                                  check_pause=check_pause_logic,
                                  start_index=start_index,
                                  get_live_profile=self._profile)
        except Exception as e:
            self._done(f"Stopped: {type(e).__name__}")
            return

        if self._stop_flag:
            self._done(f"Stopped after {chars:,} chars ({format_duration(el)})")
        else:
            self._done(f"Done!  {chars:,} chars in {format_duration(el)}")

    def _done(self, msg):
        self._pause_flag = False
        self._text_change_pause_latched = False
        self._is_running = False
        self.after(0, lambda: [
            self.start_btn.configure(state="normal"),
            self.stop_btn.configure(state="disabled"),
            self.pause_btn.configure(state="disabled", text="Pause"),
            self.status.configure(text=msg, text_color=TEXT),
            self.progress.set(1.0 if "Done" in msg else self.progress.get()),
            self._sync_visual_cursor()])

    def _show_tutorial(self):
        tut = ctk.CTkToplevel(self)
        tut.title("Welcome to Typeflow")
        tut.geometry("380x250")
        tut.transient(self)
        tut.grab_set()

        f = ctk.CTkFrame(tut, fg_color=CARD, corner_radius=12, border_width=1, border_color=ACCENT)
        f.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(f, text="⚡ Quick Start Guide", font=(FONT, 15, "bold"), text_color=ACCENT).pack(pady=(12, 8))

        msg = ("1. Paste your text or load a file.\n"
               "2. Use the slider to set your Desired Time.\n"
               "3. Click 'Start Typing' and click into your document.\n\n"
               "To abort typing instantly, move your mouse cursor to the TOP-LEFT CORNER of your screen.")

        ctk.CTkLabel(f, text=msg, font=(FONT, 12), text_color=TEXT, justify="left", wraplength=320).pack(pady=10, padx=14)

        ctk.CTkButton(f, text="Got it!", command=tut.destroy, fg_color=GREEN, hover_color=ACCENT_H, width=120, font=(FONT, 12, "bold")).pack(pady=(10, 15))


if __name__ == "__main__":
    TypeflowApp().mainloop()
