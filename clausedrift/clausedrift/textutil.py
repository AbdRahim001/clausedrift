"""Unicode / whitespace normalisation helpers.

Normalisation happens at two strengths:

``normalize_ws``
    Makes text visually comparable (smart quotes -> ASCII, dashes -> ``-``,
    collapsed whitespace). Used for display and for tokenising.

``content_key``
    Aggressive: case- and punctuation-insensitive. Two units with the same
    ``content_key`` differ only cosmetically, so we can label them
    ``cosmetic`` instead of a real edit.
"""

from __future__ import annotations

import re
import unicodedata

_TRANSLATION = {
    ord("\u2018"): "'",
    ord("\u2019"): "'",
    ord("\u201a"): "'",
    ord("\u201b"): "'",
    ord("\u201c"): '"',
    ord("\u201d"): '"',
    ord("\u201e"): '"',
    ord("\u2013"): "-",
    ord("\u2014"): "-",
    ord("\u2015"): "-",
    ord("\u2212"): "-",
    ord("\u00a0"): " ",
    ord("\u200b"): "",
    ord("\ufeff"): "",
}

_WS_RE = re.compile(r"[ \t\f\v]+")
_NON_CONTENT_RE = re.compile(r"[^0-9a-z ]+")


def normalize_ws(text: str) -> str:
    """Canonical spelling of *text* with single spaces."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_TRANSLATION)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def content_key(text: str) -> str:
    """Case- and punctuation-insensitive key used for cosmetic comparison."""
    key = normalize_ws(text).lower()
    key = _NON_CONTENT_RE.sub(" ", key)
    return " ".join(key.split())


def truncate(text: str, limit: int = 90) -> str:
    """Shorten *text* for one-line table cells."""
    text = normalize_ws(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "\u2026"
