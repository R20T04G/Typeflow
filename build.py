"""
Build Typeflow into a standalone .exe using PyInstaller.

Usage:
    pip install pyinstaller
    python build.py
"""

import subprocess
import sys

def main():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "Typeflow",
        "--add-data", "typeflow_engine.py;.",
        "--add-data", "ai_cleanup.py;.",
        "--hidden-import", "customtkinter",
        "--hidden-import", "docx",
        "--hidden-import", "fitz",
        "--collect-all", "customtkinter",
        "typeflow_gui.py",
    ]
    print("Building Typeflow.exe ...")
    print(f"  Command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("\nDone! Find Typeflow.exe in the dist/ folder.")

if __name__ == "__main__":
    main()
