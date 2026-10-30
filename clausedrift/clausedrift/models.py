"""Core data structures used across ClauseDrift."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ChangeKind(str, Enum):
    """How one aligned unit of text relates between the two documents."""

    UNCHANGED = "unchanged"
    COSMETIC = "cosmetic"
    EDITED = "edited"
    REMOVED = "removed"
    ADDED = "added"

    @property
    def label(self) -> str:
        return self.value.capitalize()


#: Kinds that count towards the drift score.
SUBSTANTIVE = (ChangeKind.ADDED, ChangeKind.REMOVED, ChangeKind.EDITED)


@dataclass(frozen=True)
class Unit:
    """A comparable chunk of text (a sentence) plus its normalised key."""

    index: int
    text: str
    key: str
    paragraph: int = 0


@dataclass
class Change:
    """A single row in the diff."""

    kind: ChangeKind
    old: Unit | None = None
    new: Unit | None = None
    similarity: float = 0.0

    @property
    def text(self) -> str:
        unit = self.new if self.new is not None else self.old
        return unit.text if unit is not None else ""

    def as_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "similarity": round(self.similarity, 4),
            "old": self.old.text if self.old else None,
            "new": self.new.text if self.new else None,
        }


@dataclass
class Report:
    """The result of comparing two documents."""

    changes: list[Change] = field(default_factory=list)
    old_units: int = 0
    new_units: int = 0
    min_similarity: float = 0.5
    source_old: str = ""
    source_new: str = ""

    # ---- derived numbers -------------------------------------------------

    def counts(self) -> dict[str, int]:
        counts = {kind.value: 0 for kind in ChangeKind}
        for change in self.changes:
            counts[change.kind.value] += 1
        return counts

    @property
    def substantive(self) -> int:
        return sum(1 for c in self.changes if c.kind in SUBSTANTIVE)

    @property
    def drift_score(self) -> float:
        """0 = nothing changed, 100 = everything replaced."""
        denominator = max(1, self.old_units + self.new_units)
        return round(100.0 * self.substantive / denominator, 2)

    @property
    def similarity(self) -> float:
        """Inverse of :attr:`drift_score`, as a 0-100 percentage."""
        return round(100.0 - self.drift_score, 2)

    def verdict(self) -> str:
        score = self.drift_score
        if score == 0:
            return "identical"
        if score < 2:
            return "trivial edits"
        if score < 10:
            return "minor edits"
        if score < 30:
            return "moderate changes"
        if score < 60:
            return "significant changes"
        return "rewritten"

    def as_dict(self) -> dict:
        return {
            "source_old": self.source_old,
            "source_new": self.source_new,
            "old_units": self.old_units,
            "new_units": self.new_units,
            "min_similarity": self.min_similarity,
            "drift_score": self.drift_score,
            "similarity": self.similarity,
            "verdict": self.verdict(),
            "counts": self.counts(),
            "changes": [c.as_dict() for c in self.changes],
        }

    def changed(self) -> list[Change]:
        return [c for c in self.changes if c.kind is not ChangeKind.UNCHANGED]
