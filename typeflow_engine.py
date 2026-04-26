"""
Typeflow Engine — Core typing simulation logic.
Shared by both the CLI (typeflow.py) and GUI (typeflow_gui.py).
"""

import time
import random
import pyautogui

# ---------------------------------------------------------------------------
# Safety: PyAutoGUI fail-safe — move mouse to top-left corner to abort
# ---------------------------------------------------------------------------
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0  # We handle our own delays

# ---------------------------------------------------------------------------
# Adjacent-key map for realistic typo generation (QWERTY layout)
# ---------------------------------------------------------------------------
ADJACENT_KEYS = {
    'a': ['s', 'q', 'w', 'z'], 'b': ['v', 'g', 'h', 'n'],
    'c': ['x', 'd', 'f', 'v'], 'd': ['s', 'e', 'r', 'f', 'c', 'x'],
    'e': ['w', 'r', 'd', 's'], 'f': ['d', 'r', 't', 'g', 'v', 'c'],
    'g': ['f', 't', 'y', 'h', 'b', 'v'], 'h': ['g', 'y', 'u', 'j', 'n', 'b'],
    'i': ['u', 'o', 'k', 'j'], 'j': ['h', 'u', 'i', 'k', 'n', 'm'],
    'k': ['j', 'i', 'o', 'l', 'm'], 'l': ['k', 'o', 'p'],
    'm': ['n', 'j', 'k'], 'n': ['b', 'h', 'j', 'm'],
    'o': ['i', 'p', 'l', 'k'], 'p': ['o', 'l'],
    'q': ['w', 'a'], 'r': ['e', 't', 'f', 'd'],
    's': ['a', 'w', 'e', 'd', 'x', 'z'], 't': ['r', 'y', 'g', 'f'],
    'u': ['y', 'i', 'j', 'h'], 'v': ['c', 'f', 'g', 'b'],
    'w': ['q', 'e', 's', 'a'], 'x': ['z', 's', 'd', 'c'],
    'y': ['t', 'u', 'h', 'g'], 'z': ['a', 's', 'x'],
}


class TypingProfile:
    """All configurable parameters for the typing simulation."""

    def __init__(self):
        # --- Speed ---
        self.base_wpm: float = 55.0
        self.speed_multiplier: float = 1.0
        self.wpm_variance: float = 0.25

        # --- Errors ---
        self.error_rate: float = 0.012
        self.long_word_error_boost: float = 0.008
        self.max_consecutive_errors: int = 2

        # --- Pauses (seconds) ---
        self.pause_after_period: tuple = (0.6, 2.0)
        self.pause_after_comma: tuple = (0.15, 0.45)
        self.pause_after_paragraph: tuple = (1.5, 4.5)
        self.pause_thinking: tuple = (2.0, 6.0)
        self.thinking_probability: float = 0.008
        self.pause_distraction: tuple = (5.0, 20.0)
        self.distraction_probability: float = 0.001

        # --- Google Docs save awareness ---
        self.save_pause_interval: int = 300
        self.save_pause_duration: tuple = (1.0, 3.0)

        # --- Fatigue ---
        self.fatigue_onset_chars: int = 2000
        self.fatigue_factor: float = 0.05
        self.fatigue_max_chars: int = 10000

        # --- Countdown ---
        self.countdown_seconds: int = 5

    def effective_wpm(self, chars_typed: int) -> float:
        """Return WPM adjusted for speed multiplier, variance, and fatigue."""
        wpm = self.base_wpm * self.speed_multiplier
        drift = random.uniform(-self.wpm_variance, self.wpm_variance)
        wpm *= (1.0 + drift)
        if chars_typed > self.fatigue_onset_chars:
            progress = min(1.0, (chars_typed - self.fatigue_onset_chars)
                           / (self.fatigue_max_chars - self.fatigue_onset_chars))
            wpm *= (1.0 - self.fatigue_factor * progress)
        return max(wpm, 10.0)

    def char_delay(self, chars_typed: int) -> float:
        """Seconds between keystrokes at current effective WPM."""
        wpm = self.effective_wpm(chars_typed)
        cpm = wpm * 5.0
        base = 60.0 / cpm
        jitter = random.uniform(-0.40, 0.40)
        return max(0.02, base * (1.0 + jitter))

    def error_chance(self, word: str, char_index_in_word: int) -> float:
        """Error probability for a character in the given word."""
        rate = self.error_rate
        word_len = len(word)
        if word_len > 5:
            rate += self.long_word_error_boost * (word_len - 5)
        if char_index_in_word > 2:
            rate *= 1.3
        return min(rate, 0.15)


def generate_typo(correct_char: str) -> str:
    """Return a plausible wrong character based on adjacent keys."""
    lower = correct_char.lower()
    if lower in ADJACENT_KEYS:
        wrong = random.choice(ADJACENT_KEYS[lower])
        return wrong.upper() if correct_char.isupper() else wrong
    if correct_char.isalpha():
        offset = random.choice([-1, 1])
        code = ord(correct_char) + offset
        if correct_char.isupper():
            return chr(max(65, min(90, code)))
        return chr(max(97, min(122, code)))
    return correct_char


def estimate_time(text: str, profile: TypingProfile) -> float:
    """Estimate total seconds a human would take to type this text."""
    char_count = len(text)
    word_count = len(text.split())
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    paragraph_count = text.count('\n\n') + text.count('\r\n\r\n')

    avg_wpm = profile.base_wpm * profile.speed_multiplier
    typing_seconds = (word_count / avg_wpm) * 60

    avg_period_pause = sum(profile.pause_after_period) / 2
    avg_comma_pause = sum(profile.pause_after_comma) / 2
    avg_para_pause = sum(profile.pause_after_paragraph) / 2
    pause_seconds = (sentence_count * avg_period_pause
                     + text.count(',') * avg_comma_pause
                     + paragraph_count * avg_para_pause)

    thinking_events = char_count * profile.thinking_probability
    pause_seconds += thinking_events * (sum(profile.pause_thinking) / 2)

    distraction_events = char_count * profile.distraction_probability
    pause_seconds += distraction_events * (sum(profile.pause_distraction) / 2)

    save_events = char_count / profile.save_pause_interval
    pause_seconds += save_events * (sum(profile.save_pause_duration) / 2)

    error_events = char_count * profile.error_rate
    avg_key_delay = 60.0 / (avg_wpm * 5)
    pause_seconds += error_events * avg_key_delay * 5

    return typing_seconds + pause_seconds


def compute_minimum_time(text: str) -> float:
    """
    Absolute fastest the script can type this text: max WPM, zero pauses,
    zero errors.  This is the hard floor.
    """
    word_count = len(text.split())
    if word_count == 0:
        return 0.0
    # 120 WPM * 3x speed multiplier = 360 effective WPM (theoretical max)
    max_wpm = 120.0 * 3.0
    return (word_count / max_wpm) * 60.0


def solve_profile_for_time(text: str, target_seconds: float,
                           base_profile: TypingProfile | None = None
                           ) -> TypingProfile:
    """
    Return a TypingProfile whose parameters are tuned so that
    estimate_time(text, profile) ~= target_seconds.

    Strategy (in order of priority):
      1. Adjust speed_multiplier (bounded 0.3 .. 3.0)
      2. Adjust thinking_probability (bounded 0 .. 0.05)
      3. Adjust distraction_probability (bounded 0 .. 0.02)

    The profile returned keeps error_rate, save_pause_interval, and
    countdown from base_profile (or defaults).
    """
    p = TypingProfile()
    if base_profile:
        p.error_rate = base_profile.error_rate
        p.save_pause_interval = base_profile.save_pause_interval
        p.countdown_seconds = base_profile.countdown_seconds

    if target_seconds <= 0 or not text.strip():
        return p

    word_count = len(text.split())
    char_count = len(text)
    if word_count == 0:
        return p

    # ----- Step 1: figure out the "fixed overhead" from punctuation/save -----
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    paragraph_count = text.count('\n\n') + text.count('\r\n\r\n')
    avg_period = sum(p.pause_after_period) / 2
    avg_comma = sum(p.pause_after_comma) / 2
    avg_para = sum(p.pause_after_paragraph) / 2
    fixed_pause = (sentence_count * avg_period
                   + text.count(',') * avg_comma
                   + paragraph_count * avg_para)
    save_events = char_count / p.save_pause_interval
    fixed_pause += save_events * (sum(p.save_pause_duration) / 2)

    # Time available for typing + thinking/distraction
    available = max(1.0, target_seconds - fixed_pause)

    # ----- Step 2: try a "natural" speed multiplier -----
    # Base typing time at 1x = (words / base_wpm) * 60
    base_typing = (word_count / p.base_wpm) * 60.0
    # Error overhead at 1x
    avg_key_delay_1x = 60.0 / (p.base_wpm * 5)
    error_overhead_1x = char_count * p.error_rate * avg_key_delay_1x * 5

    # Default thinking / distraction time
    default_think_time = char_count * 0.008 * (sum(p.pause_thinking) / 2)
    default_distract_time = char_count * 0.001 * (sum(p.pause_distraction) / 2)
    default_pause_time = default_think_time + default_distract_time

    # Desired typing portion = available - default_pause_time
    typing_budget = available - default_pause_time

    if typing_budget > 0:
        # speed_mult = base_typing / typing_budget  (+ error correction)
        # but error overhead scales with 1/speed too, so iterate once
        needed_speed = (base_typing + error_overhead_1x) / typing_budget
        needed_speed = max(0.3, min(3.0, needed_speed))
        p.speed_multiplier = round(needed_speed, 2)
    else:
        # The pause budget alone exceeds available: go max speed
        p.speed_multiplier = 3.0

    # Recompute with this speed
    current_est = estimate_time(text, p)
    # Set thinking/distraction to defaults
    p.thinking_probability = 0.008
    p.distraction_probability = 0.001

    # If current estimate is close enough, return
    if abs(current_est - target_seconds) / max(target_seconds, 1) < 0.05:
        return p

    # ----- Step 3: tune thinking/distraction to fill or reduce gap -----
    gap = target_seconds - estimate_time(text, p)

    # Thinking can add: char_count * prob * avg_think_pause
    avg_think = sum(p.pause_thinking) / 2  # 4.0s average
    avg_distract = sum(p.pause_distraction) / 2  # 12.5s average

    if gap > 0:
        # Need MORE time -> increase thinking, then distraction
        # Try to fill 70% with thinking, 30% with distraction
        think_fill = gap * 0.7
        distract_fill = gap * 0.3

        think_prob = think_fill / (char_count * avg_think) if char_count > 0 else 0
        distract_prob = distract_fill / (char_count * avg_distract) if char_count > 0 else 0

        p.thinking_probability = min(0.05, max(0.0, think_prob))
        p.distraction_probability = min(0.02, max(0.0, distract_prob))

        # If still not enough, slow down speed more
        remaining_gap = target_seconds - estimate_time(text, p)
        if remaining_gap > 5:
            # Reduce speed to fill remaining gap
            current_typing = (word_count / (p.base_wpm * p.speed_multiplier)) * 60
            needed_typing = current_typing + remaining_gap
            new_speed = (word_count / p.base_wpm) * 60.0 / needed_typing
            p.speed_multiplier = max(0.3, min(p.speed_multiplier, round(new_speed, 2)))
    else:
        # Need LESS time -> reduce thinking/distraction, then speed up
        p.thinking_probability = 0.0
        p.distraction_probability = 0.0

        remaining_gap = target_seconds - estimate_time(text, p)
        if remaining_gap < -5:
            # Speed up more
            current_typing = (word_count / (p.base_wpm * p.speed_multiplier)) * 60
            needed_typing = max(1.0, current_typing + remaining_gap)
            new_speed = (word_count / p.base_wpm) * 60.0 / needed_typing
            p.speed_multiplier = max(0.3, min(3.0, round(new_speed, 2)))

    return p


def format_duration(seconds: float) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}min"
    hours = minutes / 60
    remaining_min = minutes % 60
    return f"{int(hours)}h {int(remaining_min)}m"


def _type_single_char(ch: str):
    """Type a single character handling special keys."""
    if ch == '\n':
        pyautogui.press('enter')
    elif ch == '\t':
        pyautogui.press('tab')
    else:
        pyautogui.press(ch)


def type_text(text: str, profile: TypingProfile,
              on_progress=None, should_stop=None):
    """
    Simulate human typing of the given text.

    Args:
        text: The text to type.
        profile: TypingProfile with all settings.
        on_progress: Optional callback(chars_typed, total_chars, elapsed_secs).
        should_stop: Optional callable returning True to abort early.

    Returns:
        Tuple of (chars_typed, elapsed_seconds).
    """
    chars_typed = 0
    consecutive_errors = 0
    total_chars = len(text)
    last_save_pause = 0
    start_time = time.time()

    current_word = ""
    char_in_word = 0

    i = 0
    while i < total_chars:
        # Check for abort
        if should_stop and should_stop():
            elapsed = time.time() - start_time
            return chars_typed, elapsed

        ch = text[i]

        # Track word boundaries
        if ch in (' ', '\t', '\n', '\r'):
            current_word = ""
            char_in_word = 0
        else:
            if char_in_word == 0:
                word_end = i
                while word_end < total_chars and text[word_end] not in (' ', '\t', '\n', '\r', '.', ',', '!', '?', ';', ':'):
                    word_end += 1
                current_word = text[i:word_end]
            char_in_word += 1

        # --- Decide if we make a typo ---
        make_error = False
        if (ch.isalpha()
                and consecutive_errors < profile.max_consecutive_errors
                and random.random() < profile.error_chance(current_word, char_in_word)):
            make_error = True

        if make_error:
            wrong = generate_typo(ch)
            pyautogui.press(wrong) if len(wrong) == 1 else pyautogui.typewrite(wrong, interval=0)
            time.sleep(profile.char_delay(chars_typed))
            chars_typed += 1
            consecutive_errors += 1

            extra = random.randint(0, min(2, total_chars - i - 1))
            for j in range(extra):
                if i + 1 + j < total_chars:
                    next_ch = text[i + 1 + j]
                    _type_single_char(next_ch)
                    time.sleep(profile.char_delay(chars_typed))
                    chars_typed += 1

            time.sleep(random.uniform(0.3, 0.8))

            backspace_count = 1 + extra
            for _ in range(backspace_count):
                pyautogui.press('backspace')
                time.sleep(random.uniform(0.05, 0.15))

            for j in range(backspace_count):
                if i + j < total_chars:
                    _type_single_char(text[i + j])
                    time.sleep(profile.char_delay(chars_typed))
                    chars_typed += 1

            i += backspace_count
            consecutive_errors = 0
            char_in_word += backspace_count - 1
        else:
            _type_single_char(ch)
            chars_typed += 1
            consecutive_errors = 0
            i += 1
            if ch in (' ', '\t'):
                char_in_word = 0

        # --- Natural delay ---
        time.sleep(profile.char_delay(chars_typed))

        # --- Punctuation pauses ---
        if ch in ('.', '!', '?'):
            time.sleep(random.uniform(*profile.pause_after_period))
        elif ch == ',':
            time.sleep(random.uniform(*profile.pause_after_comma))

        # --- Paragraph pause ---
        if ch == '\n' and i < total_chars and i > 0 and text[i - 1] == '\n':
            time.sleep(random.uniform(*profile.pause_after_paragraph))

        # --- Random thinking pause ---
        if random.random() < profile.thinking_probability:
            time.sleep(random.uniform(*profile.pause_thinking))

        # --- Random distraction break ---
        if random.random() < profile.distraction_probability:
            time.sleep(random.uniform(*profile.pause_distraction))

        # --- Google Docs save pause ---
        if chars_typed - last_save_pause >= profile.save_pause_interval:
            time.sleep(random.uniform(*profile.save_pause_duration))
            last_save_pause = chars_typed

        # --- Progress callback ---
        if on_progress and chars_typed % 20 == 0:
            elapsed = time.time() - start_time
            on_progress(i, total_chars, elapsed)

    elapsed = time.time() - start_time
    if on_progress:
        on_progress(total_chars, total_chars, elapsed)
    return chars_typed, elapsed
