# Contributing to Typeflow

First off, thank you for considering contributing to Typeflow! It's people like you that make Typeflow such a great tool.

## Development Setup

1. **Fork the repo** and clone it locally.
2. **Set up a virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   # source .venv/bin/activate  # On macOS/Linux
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the app**:
   ```bash
   python typeflow_gui.py
   ```

## Pull Request Process

1. Ensure any changes or new features are tested and do not break existing functionality.
2. Update the `README.md` with details of changes to the interface, new feature flags, or necessary configuration changes if applicable.
3. Keep your commits clean and descriptive.
4. Your pull request will be reviewed by maintainers, and we might request some changes before merging.

## Code Style

- Write clean, understandable code.
- Prefer inline, human-readable code comments in logic blocks where the implementation is complex.
- Stick to the existing architectural patterns (e.g., keeping UI logic in `typeflow_gui.py` and simulation logic in `typeflow_engine.py`).

We look forward to your contributions!
