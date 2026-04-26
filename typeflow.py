"""
Typeflow CLI -- Command-line interface for the typing simulator.

Usage:
    python typeflow.py --file essay.txt
    python typeflow.py --clipboard --speed 1.5
    python typeflow.py --file essay.txt --dry-run
"""

import sys
import time
import argparse
import pyperclip

from typeflow_engine import (
    TypingProfile, estimate_time, format_duration, type_text,
)
from ai_cleanup import scan as ai_scan, clean_all as ai_clean_all


def load_file(path: str) -> str:
    """Load text from txt, docx, or pdf."""
    import os
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        from docx import Document
        doc = Document(path)
        return '\n'.join(p.text for p in doc.paragraphs)
    elif ext == '.pdf':
        import fitz
        doc = fitz.open(path)
        parts = [page.get_text() for page in doc]
        doc.close()
        return '\n'.join(parts)
    else:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()


def main():
    parser = argparse.ArgumentParser(
        description="Typeflow -- Human-like typing simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python typeflow.py --file essay.txt
  python typeflow.py --file document.docx --speed 1.5
  python typeflow.py --file report.pdf --dry-run
  python typeflow.py --clipboard

Safety: Move mouse to top-left corner to ABORT at any time.
        """
    )
    parser.add_argument('--file', '-f', type=str,
                        help='Path to file (.txt, .md, .docx, .pdf)')
    parser.add_argument('--clipboard', '-c', action='store_true',
                        help='Read text from clipboard')
    parser.add_argument('--speed', '-s', type=float, default=1.0,
                        help='Speed multiplier (default=1.0)')
    parser.add_argument('--wpm', type=float, default=48.0,
                        help='Base WPM (default=48)')
    parser.add_argument('--errors', '-e', type=float, default=0.014,
                        help='Typo probability per char (default=0.014)')
    parser.add_argument('--no-errors', action='store_true')
    parser.add_argument('--clean-ai', action='store_true',
                        help='Remove AI text artifacts before typing')
    parser.add_argument('--countdown', type=int, default=5)
    parser.add_argument('--dry-run', action='store_true',
                        help='Estimate time only')
    args = parser.parse_args()

    # Load text
    if args.file:
        try:
            text = load_file(args.file)
            print(f"Loaded {len(text)} chars from '{args.file}'")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif args.clipboard:
        text = pyperclip.paste()
        if not text:
            print("Error: Clipboard is empty.")
            sys.exit(1)
        print(f"Loaded {len(text)} chars from clipboard")
    else:
        print("Paste text below. Type END on a new line when done.\n")
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == 'END':
                    break
                lines.append(line)
            except EOFError:
                break
        text = '\n'.join(lines)

    if not text.strip():
        print("Error: No text.")
        sys.exit(1)

    # AI cleanup
    if args.clean_ai:
        hits = ai_scan(text)
        if hits:
            total = sum(h["count"] for h in hits)
            print(f"  Cleaned {total} AI artifacts")
            text = ai_clean_all(text)

    # Profile
    profile = TypingProfile()
    profile.base_wpm = args.wpm
    profile.speed_multiplier = args.speed
    profile.error_rate = 0.0 if args.no_errors else args.errors
    profile.countdown_seconds = args.countdown

    est = estimate_time(text, profile)
    words = len(text.split())

    print(f"\n{'='*50}")
    print(f"  TYPEFLOW")
    print(f"{'='*50}")
    print(f"  Words      : {words:,}")
    print(f"  Characters : {len(text):,}")
    print(f"  Base WPM   : {profile.base_wpm}")
    print(f"  Speed      : {profile.speed_multiplier}x")
    print(f"  Est. time  : {format_duration(est)}")
    print(f"{'='*50}")

    if args.dry_run:
        print("\n  [Dry run -- no typing]")
        print(f"\n  Time at different speeds:")
        for m in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
            p = TypingProfile()
            p.base_wpm = args.wpm
            p.speed_multiplier = m
            p.error_rate = profile.error_rate
            e = estimate_time(text, p)
            mark = " <-- current" if abs(m - args.speed) < 0.01 else ""
            print(f"    {m:>4.1f}x  ->  {format_duration(e)}{mark}")
        return

    print(f"\n  Place cursor in your target application.")
    resp = input("  Press ENTER to start (or 'q' to quit): ").strip()
    if resp.lower() == 'q':
        return

    # Countdown
    print()
    for i in range(profile.countdown_seconds, 0, -1):
        print(f"  Starting in {i}...", end='\r')
        time.sleep(1)
    print("  Typing!              ")

    def prog(done, total, el):
        if total > 0:
            print(f"  {done/total*100:5.1f}% | {format_duration(el)}", end='\r')

    chars, el = type_text(text, profile, on_progress=prog)
    print(f"\n{'='*50}")
    print(f"  Done! {chars:,} chars in {format_duration(el)}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
