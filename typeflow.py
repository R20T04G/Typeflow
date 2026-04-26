"""
Typeflow CLI -- Command-line interface for the typing simulator.

Usage:
    python typeflow.py                      # Interactive mode
    python typeflow.py --file input.txt     # Type from file
    python typeflow.py --clipboard          # Type from clipboard
    python typeflow.py --file input.txt --speed 1.5 --errors 0.02
"""

import sys
import time
import argparse
import pyperclip

from typeflow_engine import (
    TypingProfile, estimate_time, format_duration, type_text
)


def get_text_interactive() -> str:
    """Prompt user to paste text interactively."""
    print("\nPaste or type your text below.")
    print("When done, type 'END' on a new line and press Enter.\n")
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == 'END':
                break
            lines.append(line)
        except EOFError:
            break
    return '\n'.join(lines)


def countdown(seconds: int):
    """Print a countdown so the user can focus the target window."""
    print("\n" + "=" * 55)
    print("  TYPEFLOW -- Place your cursor in Google Docs NOW!")
    print("=" * 55)
    for i in range(seconds, 0, -1):
        print(f"  Starting in {i}...", end='\r')
        time.sleep(1)
    print("  Typing started!       ")
    print("-" * 55)


def cli_progress(done, total, elapsed):
    """Progress callback for CLI output."""
    if total > 0:
        pct = (done / total) * 100
        print(f"  Progress: {pct:5.1f}% | Elapsed: {format_duration(elapsed)}",
              end='\r')


def main():
    parser = argparse.ArgumentParser(
        description="Typeflow -- Human-like typing simulator for Google Docs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python typeflow.py --file essay.txt
  python typeflow.py --clipboard --speed 1.5
  python typeflow.py --file essay.txt --speed 0.7 --errors 0.03
  python typeflow.py  (interactive mode)

Safety: Move mouse to top-left corner to ABORT at any time.
        """
    )
    parser.add_argument('--file', '-f', type=str, help='Path to text file to type')
    parser.add_argument('--clipboard', '-c', action='store_true',
                        help='Read text from clipboard')
    parser.add_argument('--speed', '-s', type=float, default=1.0,
                        help='Speed multiplier (default=1.0, >1=faster, <1=slower)')
    parser.add_argument('--wpm', type=float, default=55.0,
                        help='Base words-per-minute (default=55)')
    parser.add_argument('--errors', '-e', type=float, default=0.012,
                        help='Typo probability per character (default=0.012)')
    parser.add_argument('--no-errors', action='store_true',
                        help='Disable all typos')
    parser.add_argument('--countdown', type=int, default=5,
                        help='Countdown seconds before typing (default=5)')
    parser.add_argument('--save-interval', type=int, default=300,
                        help='Characters between save-pauses for Google Docs (default=300)')
    parser.add_argument('--thinking', type=float, default=0.008,
                        help='Probability of random thinking pause per char (default=0.008)')
    parser.add_argument('--distraction', type=float, default=0.001,
                        help='Probability of distraction break per char (default=0.001)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Estimate time without typing')

    args = parser.parse_args()

    # --- Load text ---
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
            print(f"Loaded {len(text)} characters from '{args.file}'")
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.")
            sys.exit(1)
    elif args.clipboard:
        text = pyperclip.paste()
        if not text:
            print("Error: Clipboard is empty.")
            sys.exit(1)
        print(f"Loaded {len(text)} characters from clipboard")
    else:
        text = get_text_interactive()

    if not text.strip():
        print("Error: No text to type.")
        sys.exit(1)

    # --- Configure profile ---
    profile = TypingProfile()
    profile.base_wpm = args.wpm
    profile.speed_multiplier = args.speed
    profile.error_rate = 0.0 if args.no_errors else args.errors
    profile.countdown_seconds = args.countdown
    profile.save_pause_interval = args.save_interval
    profile.thinking_probability = args.thinking
    profile.distraction_probability = args.distraction

    # --- Statistics ---
    word_count = len(text.split())
    char_count = len(text)
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    paragraph_count = text.count('\n\n') + 1
    est_seconds = estimate_time(text, profile)

    print(f"\n{'=' * 55}")
    print(f"  TYPEFLOW -- Typing Simulation Summary")
    print(f"{'=' * 55}")
    print(f"  Characters   : {char_count:,}")
    print(f"  Words        : {word_count:,}")
    print(f"  Sentences    : {sentence_count:,}")
    print(f"  Paragraphs   : {paragraph_count:,}")
    print(f"  Base WPM     : {profile.base_wpm}")
    print(f"  Speed mult.  : {profile.speed_multiplier}x")
    print(f"  Error rate   : {profile.error_rate:.3f}")
    print(f"  Est. time    : {format_duration(est_seconds)}")
    print(f"{'=' * 55}")

    if args.dry_run:
        print("\n  [Dry run -- no typing performed]")
        print(f"\n  Time estimates at different speeds:")
        for mult in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
            p = TypingProfile()
            p.base_wpm = args.wpm
            p.speed_multiplier = mult
            p.error_rate = profile.error_rate
            p.thinking_probability = profile.thinking_probability
            p.distraction_probability = profile.distraction_probability
            est = estimate_time(text, p)
            marker = " <-- current" if abs(mult - args.speed) < 0.01 else ""
            print(f"    {mult:>4.1f}x  ->  {format_duration(est)}{marker}")
        return

    # --- Confirm ---
    print(f"\n  Move your cursor to Google Docs now.")
    resp = input("  Press ENTER to start (or 'q' to quit): ").strip()
    if resp.lower() == 'q':
        print("  Aborted.")
        return

    # --- Countdown & Type ---
    countdown(profile.countdown_seconds)
    chars, elapsed = type_text(text, profile, on_progress=cli_progress)
    print(f"\n{'=' * 55}")
    print(f"  Done! Typed {chars:,} characters in {format_duration(elapsed)}")
    print(f"{'=' * 55}")


if __name__ == '__main__':
    main()
