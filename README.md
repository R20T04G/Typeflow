# Typeflow

**Automatically retype any text with realistic human typing -- variable speed, natural pauses, occasional typos, and thinking breaks.**

---

## What It Does

Typeflow takes your text and replays it character-by-character as if a real person is typing it. It works with any text editor, browser, or application that accepts keyboard input.

**Example use cases:**
- Replaying a Word document into Google Docs so the edit history looks genuine
- Typing code into an online IDE with natural rhythm
- Filling in forms or documents without copy-paste detection
- Any situation where you need text to appear as if it was typed live

## Features

- **Research-backed typing patterns** -- 48 WPM default (average student speed), with natural variance and fatigue
- **Linguistic pause logic** -- pauses before conjunctions ("however", "because"), at sentence ends, paragraph breaks, and after long words
- **Burst typing** -- types in bursts of 3-8 characters like real humans, with micro-pauses between
- **Word-frequency speed** -- common words ("the", "and") typed faster, rare words slower
- **4 types of typos** -- adjacent key, transposition ("teh"), double letter, omission -- all auto-corrected
- **AI text cleanup** -- detects and removes AI artifacts (em dashes, smart quotes, zero-width characters)
- **Simple UI** -- just paste text, set your desired time, and start
- **Advanced controls** -- fine-tune every parameter when you need to
- **File loading** -- supports `.txt`, `.md`, `.docx` (Word), and `.pdf`
- **Desired time control** -- set how long you want typing to take; parameters auto-adjust

---

## Quick Start

### Download the .exe (Windows)

1. Go to [**Releases**](../../releases) and download `Typeflow.exe`
2. Double-click to open -- no Python needed
3. Paste text, adjust time, click **Start Typing**

### Run from source

```bash
git clone https://github.com/YOUR_USERNAME/Typeflow.git
cd Typeflow
pip install -r requirements.txt
python typeflow_gui.py
```

---

## How to Use

### 1. Load your text

- Click **Load File** to open a `.txt`, `.docx`, or `.pdf`
- Click **Paste** to paste from clipboard
- Or type/paste directly into the text area

### 2. Handle AI artifacts (if any)

If Typeflow detects AI-generated artifacts (em dashes, smart quotes, etc.), a cleanup bar appears. Click **Clean** to replace them with keyboard-typeable characters.

### 3. Set your desired time

Drag the **Desired Time** slider to choose how long the typing should take. Parameters auto-adjust to hit your target. You can also type an exact number of minutes in the custom box.

### 4. Start typing

1. Click **Start Typing**
2. Switch to your target application during the countdown
3. Watch the progress bar

### 5. Fine-tune (optional)

Click **Advanced Settings** to access all parameters:

| Setting | Default | Description |
|---------|---------|-------------|
| Speed Multiplier | 1.0x | Overall speed scale |
| Base WPM | 48 | Words per minute |
| Typo Rate | 1.4% | Chance of error per character |
| Thinking Pauses | 0.6% | Random thinking breaks |
| Distraction Breaks | 0.08% | Longer AFK-style gaps |
| Save Pause Interval | 300 chars | Periodic pause for auto-save |
| Countdown | 5 sec | Time to switch windows |

### 6. Stop anytime

- Click **Stop**, or
- Move your mouse to the **top-left corner** of the screen (emergency abort)

---

## Command Line

```bash
python typeflow.py --file essay.docx
python typeflow.py --file report.pdf --speed 1.5
python typeflow.py --clipboard --clean-ai
python typeflow.py --file essay.txt --dry-run
```

---

## Building a Standalone .exe

```bash
pip install pyinstaller
python build.py
```

Share `dist/Typeflow.exe` -- no Python required.

---

## Project Structure

```
Typeflow/
  typeflow_gui.py      # Desktop GUI app
  typeflow.py          # Command-line interface
  typeflow_engine.py   # Core typing engine
  ai_cleanup.py        # AI artifact detection & cleanup
  build.py             # PyInstaller build script
  requirements.txt     # Dependencies
```

## Requirements

- Python 3.10+ (if running from source)
- Windows / macOS / Linux

## License

MIT
