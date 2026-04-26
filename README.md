# Typeflow

**Type your Word documents into Google Docs automatically -- with realistic human typing, so your edit history looks genuine.**

---

## The Problem

You wrote your essay in Word, but the professor wants it on Google Docs. Now they can see the edit history -- and a single paste looks suspicious. Retyping thousands of words by hand? No thanks.

## The Solution

Typeflow replays your text character-by-character with natural human behaviour: variable speed, thinking pauses, occasional typos that get corrected, even distraction breaks. The Google Docs revision history looks like you typed it there from scratch.

---

## Quick Start (No coding required)

### Option A: Download the .exe (Windows)

1. Go to [**Releases**](../../releases) and download `Typeflow.exe`
2. Double-click to open -- no Python needed
3. Paste your text, set your desired time, click **Start Typing**
4. Switch to Google Docs during the countdown

### Option B: Run from source (Windows / Mac / Linux)

**Prerequisites:** [Python 3.10+](https://www.python.org/downloads/)

```bash
git clone https://github.com/YOUR_USERNAME/Typeflow.git
cd Typeflow
pip install -r requirements.txt
python typeflow_gui.py
```

---

## How to Use

### Step 1 -- Load your text

Open Typeflow and get your text in:

| Method | How |
|--------|-----|
| **Paste** | Copy text from Word, click the **Paste** button |
| **Load File** | Click **Load File** and select a `.txt` or `.md` file |
| **Type it** | Type or paste directly into the text area |

### Step 2 -- Set your desired time

Once text is loaded, Typeflow shows:
- **Estimated Time** -- how long a human would naturally take (with default settings)
- **Desired Time slider** -- drag to choose how long YOU want it to take

The slider auto-adjusts typing speed, thinking pauses, and distraction breaks to hit your target. You can also type an exact time in the **Custom (min)** box and click **Set**.

> **Tip:** The default estimate is the recommended minimum for realistic-looking history. You can go faster, but a yellow warning will appear. Going slower (up to +2 hours) adds more natural pauses.

### Step 3 -- Fine-tune (optional)

Switch to **Manual** mode if you want direct control over individual settings:

| Setting | What it does | Default |
|---------|-------------|---------|
| **Speed Multiplier** | Overall typing speed (higher = faster) | 1.0x |
| **Base WPM** | Words per minute baseline | 55 |
| **Typo Rate** | Chance of making a typo per character | 1.2% |
| **Thinking Pauses** | Random "hmm, what next?" pauses | 0.8% |
| **Distraction Breaks** | Longer AFK-style breaks (5-20 seconds) | 0.1% |
| **Save Pause Interval** | Pause every N chars for Google Docs auto-save | 300 |
| **Countdown** | Seconds before typing starts (to switch windows) | 5 sec |

### Step 4 -- Start typing

1. Click **Start Typing**
2. Immediately switch to your Google Docs tab and click where you want to type
3. The countdown gives you time to position your cursor
4. Watch the progress bar -- Typeflow handles the rest

### Step 5 -- Stop anytime

- Click **Stop** in the app, OR
- **Move your mouse to the top-left corner** of the screen (emergency abort)

---

## What Makes It Realistic

Typeflow doesn't just type fast -- it types like a human:

- **Variable speed** -- typing speed drifts naturally, not constant
- **Thinking at punctuation** -- pauses after periods, commas, paragraph breaks
- **Typos + corrections** -- hits adjacent keys by mistake, then backspaces to fix (longer words = more errors, just like real typing)
- **Random thinking pauses** -- stops for 2-6 seconds like you're thinking about the next sentence
- **Distraction breaks** -- occasional 5-20 second gaps (checking phone, looking away)
- **Fatigue** -- gradually slows down after 2000+ characters
- **Google Docs save sync** -- pauses periodically so auto-save captures the history

---

## Command Line (for power users)

Prefer the terminal? The CLI works too:

```bash
# Type from a file
python typeflow.py --file essay.txt

# Type from clipboard
python typeflow.py --clipboard

# Faster typing, fewer errors
python typeflow.py --file essay.txt --speed 1.5 --errors 0.005

# See time estimates without typing
python typeflow.py --file essay.txt --dry-run

# All options
python typeflow.py --help
```

---

## Building the .exe Yourself

Want to create a standalone executable to share?

```bash
pip install pyinstaller
python build.py
```

The `.exe` appears in the `dist/` folder. Share it with anyone -- no Python required.

---

## Project Structure

```
Typeflow/
  typeflow_gui.py      # Desktop GUI app (main entry point)
  typeflow.py          # Command-line interface
  typeflow_engine.py   # Core typing engine (shared logic)
  build.py             # One-click PyInstaller build script
  requirements.txt     # Python dependencies
```

## Requirements

- Python 3.10+ (if running from source)
- Windows / macOS / Linux
- Dependencies: `pyautogui`, `pyperclip`, `customtkinter`

---

## Safety

**Emergency stop:** Move your mouse to the **top-left corner** of your screen at any time. PyAutoGUI's fail-safe will immediately abort all typing.

## License

MIT
