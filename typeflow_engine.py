"""
Typeflow Engine v2 — Research-backed human typing simulation.

Key improvements over v1:
- Linguistic pause points (conjunctions, transitions, clause boundaries)
- Burst typing (3-8 chars fast, then micro-pause)
- Word-frequency speed variation (common words typed faster)
- Improved typo model (transpositions, omissions, doubles)
- Research-backed defaults (48 WPM average student)
"""

import time
import random
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

# ---------------------------------------------------------------------------
# Keyboard layout for typos
# ---------------------------------------------------------------------------
ADJACENT_KEYS = {
    'a': 'sqwz', 'b': 'vghn', 'c': 'xdfv', 'd': 'serfcx',
    'e': 'wrds', 'f': 'drtgvc', 'g': 'ftyhbv', 'h': 'gyujnb',
    'i': 'uokj', 'j': 'huiknm', 'k': 'jiolm', 'l': 'kop',
    'm': 'njk', 'n': 'bhjm', 'o': 'iplk', 'p': 'ol',
    'q': 'wa', 'r': 'etfd', 's': 'awedxz', 't': 'rygf',
    'u': 'yijh', 'v': 'cfgb', 'w': 'qesa', 'x': 'zsdc',
    'y': 'tuhg', 'z': 'asx',
}

# ---------------------------------------------------------------------------
# Common English words — typed faster (research: familiar words = less
# cognitive load = faster keystroke intervals)
# ---------------------------------------------------------------------------
COMMON_WORDS = frozenset({
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
    'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
    'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get',
    'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
    'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your',
    'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
    'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
    'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first',
    'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
    'give', 'day', 'most', 'us', 'is', 'are', 'was', 'were', 'been',
    'has', 'had', 'did', 'does', 'am', 'may', 'more', 'very', 'much',
    'many', 'each', 'still', 'too', 'here', 'where', 'why', 'should',
    'need', 'try', 'ask', 'own', 'part', 'find', 'long', 'down',
    'put', 'end', 'does', 'let', 'say', 'help', 'every', 'must',
    'home', 'life', 'old', 'big', 'high', 'last', 'never', 'same',
    'great', 'little', 'world', 'hand', 'still', 'keep', 'start',
    'might', 'while', 'away', 'right', 'didn', 'don', 'doesn', 'it',
    'going', 'really', 'being', 'thing', 'made', 'sure', 'point',
    'through', 'much', 'before', 'between', 'both', 'those', 'already',
})

# ---------------------------------------------------------------------------
# Words/phrases that trigger a thinking pause BEFORE them
# (human composes the connecting thought)
# ---------------------------------------------------------------------------
THINKING_TRIGGERS_BEFORE = frozenset({
    'however', 'but', 'although', 'because', 'since', 'therefore',
    'furthermore', 'moreover', 'meanwhile', 'nevertheless', 'nonetheless',
    'consequently', 'additionally', 'alternatively', 'regardless',
    'specifically', 'essentially', 'ultimately', 'unfortunately',
    'surprisingly', 'interestingly', 'importantly', 'significantly',
    'notably', 'particularly', 'accordingly',
})

# Multi-word transition phrases that trigger a longer pause
TRANSITION_PHRASES = [
    'in addition', 'on the other hand', 'for example', 'for instance',
    'as a result', 'in contrast', 'in conclusion', 'to summarize',
    'in other words', 'that is to say', 'in particular', 'as such',
    'due to', 'in order to', 'with respect to', 'as well as',
    'not only', 'such as', 'rather than', 'as opposed to',
    'in fact', 'of course', 'at the same time', 'on the contrary',
]


class TypingProfile:
    """All configurable parameters for the typing simulation."""

    def __init__(self):
        # --- Speed (research: avg student ~41-52 WPM, experienced ~65) ---
        self.base_wpm: float = 48.0
        self.speed_multiplier: float = 1.0
        self.wpm_variance: float = 0.25

        # --- Burst typing ---
        self.burst_length: tuple = (3, 8)       # chars per burst
        self.burst_pause: tuple = (0.04, 0.14)  # pause between bursts

        # --- Word-frequency speed adjustment ---
        self.common_word_speedup: float = 0.25   # 25% faster for common words
        self.uncommon_word_slowdown: float = 0.20  # 20% slower for rare words

        # --- Errors ---
        self.error_rate: float = 0.014
        self.long_word_error_boost: float = 0.006
        self.max_consecutive_errors: int = 2
        # Error type weights (must sum to ~1.0)
        self.error_weight_adjacent: float = 0.55
        self.error_weight_transpose: float = 0.20
        self.error_weight_double: float = 0.12
        self.error_weight_omit: float = 0.13

        # --- Linguistic pauses ---
        self.pause_after_period: tuple = (0.8, 3.0)
        self.pause_after_comma: tuple = (0.15, 0.50)
        self.pause_after_semicolon: tuple = (0.3, 0.8)
        self.pause_after_paragraph: tuple = (2.0, 8.0)
        self.pause_before_conjunction: tuple = (0.5, 2.5)
        self.pause_before_transition: tuple = (0.8, 3.0)
        self.pause_after_long_word: tuple = (0.1, 0.4)
        self.long_word_threshold: int = 8

        # --- Random human pauses ---
        self.pause_thinking: tuple = (2.0, 6.0)
        self.thinking_probability: float = 0.006
        self.pause_distraction: tuple = (5.0, 20.0)
        self.distraction_probability: float = 0.0008

        # --- Inter-word gap ---
        self.word_gap: tuple = (0.04, 0.14)

        # --- Save awareness ---
        self.save_pause_interval: int = 300
        self.save_pause_duration: tuple = (1.0, 3.0)

        # --- Fatigue ---
        self.fatigue_onset_chars: int = 2000
        self.fatigue_factor: float = 0.06
        self.fatigue_max_chars: int = 8000

        # --- Countdown ---
        self.countdown_seconds: int = 5

    def effective_wpm(self, chars_typed: int, word: str = "") -> float:
        """WPM adjusted for multiplier, variance, fatigue, word familiarity."""
        wpm = self.base_wpm * self.speed_multiplier
        # Random drift
        wpm *= (1.0 + random.uniform(-self.wpm_variance, self.wpm_variance))
        # Word familiarity
        if word:
            w = word.lower().strip('.,!?;:')
            if w in COMMON_WORDS:
                wpm *= (1.0 + self.common_word_speedup)
            elif len(w) > 6:
                wpm *= (1.0 - self.uncommon_word_slowdown)
        # Fatigue
        if chars_typed > self.fatigue_onset_chars:
            progress = min(1.0, (chars_typed - self.fatigue_onset_chars)
                           / (self.fatigue_max_chars - self.fatigue_onset_chars))
            wpm *= (1.0 - self.fatigue_factor * progress)
        return max(wpm, 8.0)

    def char_delay(self, chars_typed: int, word: str = "") -> float:
        """Seconds between keystrokes."""
        wpm = self.effective_wpm(chars_typed, word)
        cpm = wpm * 5.0
        base = 60.0 / cpm
        jitter = random.uniform(-0.35, 0.35)
        return max(0.02, base * (1.0 + jitter))

    def error_chance(self, word: str, pos_in_word: int) -> float:
        """Error probability for a character."""
        rate = self.error_rate
        wlen = len(word)
        if wlen > 5:
            rate += self.long_word_error_boost * (wlen - 5)
        if pos_in_word > 2:
            rate *= 1.3
        return min(rate, 0.15)


# ---------------------------------------------------------------------------
# Typo generation
# ---------------------------------------------------------------------------
def _typo_adjacent(ch: str) -> str:
    lower = ch.lower()
    if lower in ADJACENT_KEYS:
        candidates = ADJACENT_KEYS[lower]
        wrong = random.choice(candidates)
        return wrong.upper() if ch.isupper() else wrong
    # Fallback for non-mapped alpha: shift by 1
    if ch.isalpha():
        offset = random.choice([-1, 1])
        code = ord(ch) + offset
        if ch.isupper():
            return chr(max(65, min(90, code)))
        return chr(max(97, min(122, code)))
    # Non-alpha: return a nearby key
    return random.choice('asdfghjkl')

def _typo_transpose(word: str, pos: int) -> tuple[str, int] | None:
    """Swap chars at pos and pos+1. Returns (wrong_pair, extra_advance) or None."""
    if pos + 1 < len(word) and word[pos].isalpha() and word[pos + 1].isalpha():
        return (word[pos + 1] + word[pos]), 1
    return None

def _typo_double(ch: str) -> str:
    """Type the character twice."""
    return ch + ch

def _typo_omit() -> str:
    """Skip the character (return empty)."""
    return ""

def generate_typo(word: str, pos: int, profile: TypingProfile) -> tuple[str, int]:
    """
    Generate a typo for word[pos].
    Returns (chars_to_type, advance) where advance is how many extra
    source chars were consumed (0 for simple replacement, 1 for transpose).
    """
    ch = word[pos]
    roll = random.random()
    cumulative = 0.0

    # Adjacent key
    cumulative += profile.error_weight_adjacent
    if roll < cumulative:
        return _typo_adjacent(ch), 0

    # Transpose
    cumulative += profile.error_weight_transpose
    if roll < cumulative:
        result = _typo_transpose(word, pos)
        if result:
            return result[0], result[1]
        return _typo_adjacent(ch), 0  # fallback

    # Double letter
    cumulative += profile.error_weight_double
    if roll < cumulative:
        return _typo_double(ch), 0

    # Omit — skip typing the char, but we still need to type *something*
    # wrong so the backspace logic works. Use adjacent-key as fallback.
    return _typo_adjacent(ch), 0


# ---------------------------------------------------------------------------
# Time estimation
# ---------------------------------------------------------------------------
def estimate_time(text: str, profile: TypingProfile) -> float:
    """Estimate seconds a human would take to type this text."""
    if not text.strip():
        return 0.0
    char_count = len(text)
    word_count = len(text.split())
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    paragraph_count = text.count('\n\n') + text.count('\r\n\r\n')
    comma_count = text.count(',')
    semicolon_count = text.count(';')

    avg_wpm = profile.base_wpm * profile.speed_multiplier
    typing_seconds = (word_count / max(avg_wpm, 1)) * 60

    # Punctuation pauses
    pause_s = (sentence_count * sum(profile.pause_after_period) / 2
               + comma_count * sum(profile.pause_after_comma) / 2
               + semicolon_count * sum(profile.pause_after_semicolon) / 2
               + paragraph_count * sum(profile.pause_after_paragraph) / 2)

    # Conjunction/transition pauses (estimate from word count)
    words = text.lower().split()
    conj_count = sum(1 for w in words if w.strip('.,!?;:') in THINKING_TRIGGERS_BEFORE)
    pause_s += conj_count * sum(profile.pause_before_conjunction) / 2

    # Thinking & distraction
    pause_s += char_count * profile.thinking_probability * sum(profile.pause_thinking) / 2
    pause_s += char_count * profile.distraction_probability * sum(profile.pause_distraction) / 2

    # Save pauses
    pause_s += (char_count / profile.save_pause_interval) * sum(profile.save_pause_duration) / 2

    # Error correction overhead
    error_events = char_count * profile.error_rate
    avg_key_delay = 60.0 / (avg_wpm * 5)
    pause_s += error_events * avg_key_delay * 5

    # Burst pauses
    burst_events = char_count / ((profile.burst_length[0] + profile.burst_length[1]) / 2)
    pause_s += burst_events * sum(profile.burst_pause) / 2

    return typing_seconds + pause_s


def compute_minimum_time(text: str) -> float:
    """Absolute floor: max speed, zero pauses."""
    char_count = len(text)
    word_count = len(text.split())
    if word_count == 0:
        return 0.0
    # WPM-based floor
    wpm_floor = (word_count / 360.0) * 60.0
    # char_delay floor: 0.02s per character minimum
    char_floor = char_count * 0.02
    return max(wpm_floor, char_floor)


def solve_profile_for_time(text: str, target_seconds: float,
                           base_profile=None) -> 'TypingProfile':
    """Tune a profile so estimate_time ~= target_seconds."""
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

    # Compute fixed overhead (punctuation + conjunctions + save)
    default_est = estimate_time(text, p)
    base_typing = (word_count / p.base_wpm) * 60.0

    # Simple ratio approach: scale speed to hit target
    if default_est > 0:
        ratio = default_est / target_seconds
        p.speed_multiplier = max(0.3, min(3.0, round(ratio, 2)))

    # Check estimate, adjust thinking/distraction for remaining gap
    p.thinking_probability = 0.006
    p.distraction_probability = 0.0008
    current = estimate_time(text, p)
    gap = target_seconds - current

    avg_think = sum(p.pause_thinking) / 2
    avg_distract = sum(p.pause_distraction) / 2

    if gap > 0:
        think_fill = gap * 0.7
        distract_fill = gap * 0.3
        p.thinking_probability = min(0.05, max(0.0,
            think_fill / (char_count * avg_think) if char_count > 0 else 0))
        p.distraction_probability = min(0.02, max(0.0,
            distract_fill / (char_count * avg_distract) if char_count > 0 else 0))

        remaining = target_seconds - estimate_time(text, p)
        if remaining > 5:
            cur_typing = (word_count / (p.base_wpm * p.speed_multiplier)) * 60
            new_speed = (word_count / p.base_wpm) * 60.0 / (cur_typing + remaining)
            p.speed_multiplier = max(0.3, min(p.speed_multiplier, round(new_speed, 2)))
    elif gap < -5:
        p.thinking_probability = 0.0
        p.distraction_probability = 0.0
        remaining = target_seconds - estimate_time(text, p)
        if remaining < -5:
            cur_typing = (word_count / (p.base_wpm * p.speed_multiplier)) * 60
            needed = max(1.0, cur_typing + remaining)
            new_speed = (word_count / p.base_wpm) * 60.0 / needed
            p.speed_multiplier = max(0.3, min(3.0, round(new_speed, 2)))

    return p


def format_duration(seconds: float) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} min"
    hours = minutes / 60
    remaining_min = minutes % 60
    return f"{int(hours)}h {int(remaining_min)}m"


# ---------------------------------------------------------------------------
# Typing engine
# ---------------------------------------------------------------------------
def _type_char(ch: str):
    """Type a single character."""
    if ch == '\n':
        pyautogui.press('enter')
    elif ch == '\t':
        pyautogui.press('tab')
    else:
        pyautogui.press(ch)


def _find_current_word(text: str, pos: int) -> str:
    """Extract the word surrounding position pos."""
    start = pos
    while start > 0 and text[start - 1] not in (' ', '\t', '\n', '\r'):
        start -= 1
    end = pos
    while end < len(text) and text[end] not in (' ', '\t', '\n', '\r'):
        end += 1
    return text[start:end]


def _check_transition_ahead(text: str, pos: int) -> bool:
    """Check if a multi-word transition phrase starts near pos."""
    snippet = text[pos:pos + 30].lower()
    for phrase in TRANSITION_PHRASES:
        if snippet.startswith(phrase):
            return True
    return False


def type_text(text: str, profile: TypingProfile,
              on_progress=None, should_stop=None):
    """
    Simulate human typing with research-backed patterns.

    Returns: (chars_typed, elapsed_seconds)
    """
    total_chars = len(text)
    chars_typed = 0
    consecutive_errors = 0
    last_save_pause = 0
    burst_counter = random.randint(*profile.burst_length)
    start_time = time.time()

    i = 0
    while i < total_chars:
        if should_stop and should_stop():
            return chars_typed, time.time() - start_time

        ch = text[i]
        current_word = _find_current_word(text, i)
        word_start = i
        while word_start > 0 and text[word_start - 1] not in (' ', '\t', '\n', '\r'):
            word_start -= 1
        pos_in_word = i - word_start

        # --- Linguistic pause BEFORE this word ---
        if pos_in_word == 0 and ch not in (' ', '\t', '\n', '\r'):
            w_lower = current_word.lower().strip('.,!?;:')
            if w_lower in THINKING_TRIGGERS_BEFORE:
                time.sleep(random.uniform(*profile.pause_before_conjunction))
            elif _check_transition_ahead(text, i):
                time.sleep(random.uniform(*profile.pause_before_transition))

        # --- Decide typo ---
        make_error = (
            ch.isalpha()
            and consecutive_errors < profile.max_consecutive_errors
            and random.random() < profile.error_chance(current_word, pos_in_word)
        )

        if make_error:
            wrong_chars, advance = generate_typo(current_word, pos_in_word, profile)

            # Type the wrong characters
            for wc in wrong_chars:
                _type_char(wc)
                time.sleep(profile.char_delay(chars_typed, current_word))
                chars_typed += 1
            consecutive_errors += 1

            # Maybe type 0-2 more correct chars before noticing
            max_extra = max(0, min(2, total_chars - i - 1 - advance))
            extra = random.randint(0, max_extra) if max_extra > 0 else 0
            for j in range(extra):
                idx = i + 1 + advance + j
                if idx < total_chars:
                    _type_char(text[idx])
                    time.sleep(profile.char_delay(chars_typed, current_word))
                    chars_typed += 1

            # Pause — noticing mistake
            time.sleep(random.uniform(0.3, 0.9))

            # Backspace
            bs_count = len(wrong_chars) + extra
            for _ in range(bs_count):
                pyautogui.press('backspace')
                time.sleep(random.uniform(0.04, 0.12))

            # Retype correctly
            for j in range(1 + advance + extra):
                idx = i + j
                if idx < total_chars:
                    _type_char(text[idx])
                    time.sleep(profile.char_delay(chars_typed, current_word))
                    chars_typed += 1

            i += 1 + advance + extra
            consecutive_errors = 0
        else:
            _type_char(ch)
            chars_typed += 1
            consecutive_errors = 0
            i += 1

        # --- Inter-keystroke delay ---
        time.sleep(profile.char_delay(chars_typed, current_word))

        # --- Burst pause ---
        burst_counter -= 1
        if burst_counter <= 0:
            time.sleep(random.uniform(*profile.burst_pause))
            burst_counter = random.randint(*profile.burst_length)

        # --- Word gap ---
        if ch == ' ':
            time.sleep(random.uniform(*profile.word_gap))

        # --- Punctuation pauses ---
        if ch in ('.', '!', '?'):
            time.sleep(random.uniform(*profile.pause_after_period))
        elif ch == ',':
            time.sleep(random.uniform(*profile.pause_after_comma))
        elif ch in (';', ':'):
            time.sleep(random.uniform(*profile.pause_after_semicolon))

        # --- Paragraph pause ---
        if ch == '\n' and i < total_chars and text[i] == '\n':
            time.sleep(random.uniform(*profile.pause_after_paragraph))

        # --- Long word pause (after finishing) ---
        if ch == ' ' and i >= 2:
            prev_word = _find_current_word(text, i - 2)
            if len(prev_word) >= profile.long_word_threshold:
                time.sleep(random.uniform(*profile.pause_after_long_word))

        # --- Random thinking ---
        if random.random() < profile.thinking_probability:
            time.sleep(random.uniform(*profile.pause_thinking))

        # --- Random distraction ---
        if random.random() < profile.distraction_probability:
            time.sleep(random.uniform(*profile.pause_distraction))

        # --- Save pause ---
        if chars_typed - last_save_pause >= profile.save_pause_interval:
            time.sleep(random.uniform(*profile.save_pause_duration))
            last_save_pause = chars_typed

        # --- Progress callback ---
        if on_progress and chars_typed % 20 == 0:
            on_progress(i, total_chars, time.time() - start_time)

    elapsed = time.time() - start_time
    if on_progress:
        on_progress(total_chars, total_chars, elapsed)
    return chars_typed, elapsed
