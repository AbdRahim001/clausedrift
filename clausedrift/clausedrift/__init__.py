"""ClauseDrift - explainable drift detection for AI-generated text.

Typical use::

    from clausedrift import compare

    report = compare(old_prompt_output, new_prompt_output)
    print(report.drift_score, report.verdict())
"""

from __future__ import annotations

from pathlib import Path

from .engine import Comparer, compare
from .models import Change, ChangeKind, Report, Unit
from .render import render_json, render_markdown, render_text
from .segment import segment
from .similarity import Similarity, tokenize

__version__ = "0.1.0"

__all__ = [
    "Change",
    "ChangeKind",
    "Comparer",
    "Report",
    "Similarity",
    "Unit",
    "__version__",
    "compare",
    "compare_files",
    "render_json",
    "render_markdown",
    "render_text",
    "segment",
    "tokenize",
]


def compare_files(
    old_path: str | Path,
    new_path: str | Path,
    min_similarity: float = 0.5,
) -> Report:
    """Compare two text files on disk, tagging the report with their names."""
    old_file = Path(old_path)
    new_file = Path(new_path)
    report = compare(
        old_file.read_text(encoding="utf-8"),
        new_file.read_text(encoding="utf-8"),
        min_similarity=min_similarity,
    )
    report.source_old = old_file.name
    report.source_new = new_file.name
    return report
