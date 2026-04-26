"""
AI Text Cleanup — Detect and replace common AI-generated text artifacts.

Detects em dashes, smart quotes, fancy Unicode, zero-width characters, etc.
and offers to replace them with keyboard-typeable equivalents.
"""

import re

# ---------------------------------------------------------------------------
# Artifact definitions: (name, pattern, replacement, description)
# ---------------------------------------------------------------------------
ARTIFACTS = [
    (
        "em_dash",
        "\u2014",            # —
        " - ",
        "Em dash to spaced hyphen",
    ),
    (
        "en_dash",
        "\u2013",            # –
        "-",
        "En dash to hyphen",
    ),
    (
        "smart_double_open",
        "\u201C",            # "
        '"',
        "Smart open double quote",
    ),
    (
        "smart_double_close",
        "\u201D",            # "
        '"',
        "Smart close double quote",
    ),
    (
        "smart_single_open",
        "\u2018",            # '
        "'",
        "Smart open single quote",
    ),
    (
        "smart_single_close",
        "\u2019",            # '
        "'",
        "Smart close single quote / apostrophe",
    ),
    (
        "ellipsis",
        "\u2026",            # …
        "...",
        "Ellipsis character to three dots",
    ),
    (
        "bullet",
        "\u2022",            # •
        "- ",
        "Bullet point to hyphen",
    ),
    (
        "nbsp",
        "\u00A0",            # non-breaking space
        " ",
        "Non-breaking space",
    ),
    (
        "narrow_nbsp",
        "\u202F",            # narrow no-break space
        " ",
        "Narrow no-break space",
    ),
    (
        "zero_width_space",
        "\u200B",
        "",
        "Zero-width space",
    ),
    (
        "zero_width_joiner",
        "\u200D",
        "",
        "Zero-width joiner",
    ),
    (
        "zero_width_non_joiner",
        "\u200C",
        "",
        "Zero-width non-joiner",
    ),
    (
        "bom",
        "\uFEFF",
        "",
        "Byte order mark",
    ),
]


def scan(text: str) -> list[dict]:
    """
    Scan text for AI artifacts.

    Returns a list of dicts:
        [{"name": str, "description": str, "count": int,
          "pattern": str, "replacement": str}, ...]
    Only artifacts with count > 0 are included.
    """
    results = []
    for name, pattern, replacement, description in ARTIFACTS:
        count = text.count(pattern)
        if count > 0:
            results.append({
                "name": name,
                "description": description,
                "count": count,
                "pattern": pattern,
                "replacement": replacement,
            })
    return results


def clean(text: str, selected_names: list[str] | None = None) -> str:
    """
    Replace selected artifacts in text.
    If selected_names is None, clean ALL detected artifacts.
    """
    for name, pattern, replacement, _ in ARTIFACTS:
        if selected_names is None or name in selected_names:
            text = text.replace(pattern, replacement)
    return text


def clean_all(text: str) -> str:
    """Replace every known artifact."""
    return clean(text, selected_names=None)
