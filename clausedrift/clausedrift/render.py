"""Report rendering: terminal tables, Markdown and JSON."""

from __future__ import annotations

import json

from .models import ChangeKind, Report
from .textutil import truncate

# ANSI colours, disabled when NO_COLOR is set or output is not a TTY.
_RESET = "\033[0m"
_COLOURS = {
    ChangeKind.ADDED: "\033[32m",
    ChangeKind.REMOVED: "\033[31m",
    ChangeKind.EDITED: "\033[33m",
    ChangeKind.UNCHANGED: "\033[90m",
    ChangeKind.COSMETIC: "\033[36m",
}
_MARKERS = {
    ChangeKind.ADDED: "+",
    ChangeKind.REMOVED: "-",
    ChangeKind.EDITED: "~",
    ChangeKind.UNCHANGED: "=",
    ChangeKind.COSMETIC: "~",
}


def render_json(report: Report, indent: int = 2) -> str:
    """Machine-readable report (this is what CI gates should parse)."""
    return json.dumps(report.as_dict(), indent=indent, ensure_ascii=False)


def render_markdown(report: Report, only_changes: bool = True) -> str:
    """A Markdown report suitable for a PR comment or a saved artifact."""
    counts = report.counts()
    lines = [
        f"# ClauseDrift report: {report.source_old or 'old'} -> "
        f"{report.source_new or 'new'}",
        "",
        f"**Drift score: {report.drift_score}/100** ({report.verdict()}) "
        f"- {report.similarity}% of content preserved.",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Sentences (old -> new) | {report.old_units} -> {report.new_units} |",
        f"| Unchanged | {counts[ChangeKind.UNCHANGED.value]} |",
        f"| Cosmetic only | {counts[ChangeKind.COSMETIC.value]} |",
        f"| Edited | {counts[ChangeKind.EDITED.value]} |",
        f"| Removed | {counts[ChangeKind.REMOVED.value]} |",
        f"| Added | {counts[ChangeKind.ADDED.value]} |",
        "",
        "## Changes",
        "",
    ]
    rows = report.changed() if only_changes else report.changes
    if not rows:
        lines.append("_No differences found._")
        return "\n".join(lines) + "\n"

    lines += ["| # | Type | Old | New | Sim |", "| --- | --- | --- | --- | --- |"]
    for number, change in enumerate(rows, start=1):
        old = f"`{truncate(change.old.text) if change.old else ''}`"
        new = f"`{truncate(change.new.text) if change.new else ''}`"
        lines.append(
            f"| {number} | **{change.kind.label}** | {old} | {new} | "
            f"{change.similarity:.2f} |"
        )
    return "\n".join(lines) + "\n"


def render_text(report: Report, only_changes: bool = True, colour: bool = True) -> str:
    """Human-friendly terminal output."""
    lines = [
        f"ClauseDrift  {report.source_old or 'old'} -> {report.source_new or 'new'}",
        f"sentences: {report.old_units} old / {report.new_units} new",
        f"drift score: {report.drift_score}/100  ({report.verdict()})",
        "",
    ]
    rows = report.changed() if only_changes else report.changes
    if not rows:
        lines.append("  no differences")
        return "\n".join(lines)

    for change in rows:
        marker = _MARKERS[change.kind]
        prefix = f"{_COLOURS[change.kind]}{marker}{_RESET}" if colour else marker
        if change.kind is ChangeKind.EDITED:
            lines.append(f"{prefix} {change.kind.label} ({change.similarity:.2f})")
            lines.append(f"    - {truncate(change.old.text, 100)}")
            lines.append(f"    + {truncate(change.new.text, 100)}")
        elif change.kind is ChangeKind.REMOVED:
            lines.append(f"{prefix} {change.kind.label}")
            lines.append(f"    - {truncate(change.old.text, 100)}")
        elif change.kind is ChangeKind.ADDED:
            lines.append(f"{prefix} {change.kind.label}")
            lines.append(f"    + {truncate(change.new.text, 100)}")
        else:
            lines.append(f"{prefix} {change.kind.label}")
            lines.append(f"    = {truncate(change.new.text, 100)}")
    return "\n".join(lines)


def counts_table(report: Report) -> str:
    """Compact one-line summary."""
    counts = report.counts()
    return "  ".join(
        f"{kind.value}:{counts[kind.value]}" for kind in ChangeKind
    )
