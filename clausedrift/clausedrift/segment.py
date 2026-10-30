"""Split a document into ordered, comparable units (sentences)."""

from __future__ import annotations

import re

from .models import Unit
from .textutil import content_key, normalize_ws

#: Sentence boundary: terminal punctuation followed by whitespace.
_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")

#: Abbreviations that should never end a sentence.
_ABBREVIATIONS = frozenset(
    {
        "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc",
        "inc", "ltd", "llc", "co", "corp", "plc", "dept", "est", "approx",
        "no", "fig", "al", "e.g", "i.e", "cf", "u.s", "u.k", "a.m", "p.m",
    }
)

_TAIL_WORD_RE = re.compile(r"([A-Za-z][A-Za-z.]*)$")


def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines, then join soft-wrapped lines into one line."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs: list[str] = []
    for chunk in re.split(r"\n[ \t]*\n", text):
        lines = [line.strip() for line in chunk.split("\n") if line.strip()]
        if not lines:
            continue
        paragraphs.append(normalize_ws(" ".join(_dedent_bullets(lines))))
    return paragraphs


def _dedent_bullets(lines: list[str]) -> list[str]:
    """Strip leading list markers so numbering changes are not 'edits'."""
    return [re.sub(r"^(?:[-*\u2022]|\d{1,2}[.)])\s+", "", line) for line in lines]


def _ends_with_abbreviation(fragment: str) -> bool:
    match = _TAIL_WORD_RE.search(fragment)
    if not match:
        return False
    raw = match.group(1).rstrip(".")
    if raw.lower() in _ABBREVIATIONS:
        return True
    # Single capitalised initial, e.g. "J." in "J. Doe" - but not "A b".
    return len(raw) == 1 and raw.isupper()


def split_sentences(paragraph: str) -> list[str]:
    """Split one paragraph into sentences, respecting common abbreviations."""
    fragments = [f.strip() for f in _BOUNDARY_RE.split(paragraph) if f.strip()]
    sentences: list[str] = []
    for fragment in fragments:
        if sentences and _ends_with_abbreviation(sentences[-1]):
            sentences[-1] = f"{sentences[-1]} {fragment}"
        else:
            sentences.append(fragment)
    return sentences


def segment(text: str) -> list[Unit]:
    """Turn a whole document into an ordered list of :class:`Unit`.

    Units are sentences, tagged with the paragraph they came from so reports
    can show context later. Empty documents yield an empty list.
    """
    units: list[Unit] = []
    for paragraph_index, paragraph in enumerate(split_paragraphs(text)):
        for sentence in split_sentences(paragraph):
            sentence = normalize_ws(sentence)
            if not sentence:
                continue
            units.append(
                Unit(
                    index=len(units),
                    text=sentence,
                    key=content_key(sentence),
                    paragraph=paragraph_index,
                )
            )
    return units
