"""The comparison engine: align two documents and classify every change."""

from __future__ import annotations

from collections.abc import Sequence
from difflib import SequenceMatcher

from .backends import Backend, build_backend
from .models import Change, ChangeKind, Report, Unit
from .segment import segment


class Comparer:
    """Compare two documents and produce a :class:`Report`.

    Args:
        min_similarity: A removed unit and an added unit are paired as a
            single ``edited`` change when their similarity is at least this
            value. Raise it to see every reword as remove+add; lower it to
            treat loosely related sentences as rewrites of each other.
        backend: Optional pre-built similarity backend.

    Example:
        >>> comparer = Comparer()
        >>> report = comparer.compare("The fee is $50.", "The fee is $75.")
        >>> report.changes[0].kind.value
        'edited'
    """

    def __init__(
        self,
        min_similarity: float = 0.5,
        backend: Backend | None = None,
        backend_name: str | None = None,
    ) -> None:
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between 0 and 1")
        self.min_similarity = min_similarity
        self._backend = backend
        self._backend_name = backend_name

    # ---- public API ------------------------------------------------------

    def compare(self, old_text: str, new_text: str) -> Report:
        """Compare two raw document strings."""
        old_units = segment(old_text)
        new_units = segment(new_text)
        return self.compare_units(old_units, new_units)

    def compare_units(self, old_units: Sequence[Unit], new_units: Sequence[Unit]) -> Report:
        """Compare two already-segmented documents."""
        backend = self._backend or build_backend(
            [u.text for u in old_units] + [u.text for u in new_units],
            self._backend_name,
        )
        report = Report(
            old_units=len(old_units),
            new_units=len(new_units),
            min_similarity=self.min_similarity,
        )
        for kind, old, new in self._align(old_units, new_units, backend):
            report.changes.append(
                Change(
                    kind=kind,
                    old=old,
                    new=new,
                    similarity=self._pair_similarity(old, new, backend),
                )
            )
        return report

    # ---- internals -------------------------------------------------------

    def _align(
        self,
        old_units: Sequence[Unit],
        new_units: Sequence[Unit],
        backend: Backend,
    ) -> list[tuple[ChangeKind, Unit | None, Unit | None]]:
        """Two-stage alignment.

        Stage 1 finds exactly-equal sentences at scale (cheap, exact). Stage 2
        pairs the leftover runs of removed/added sentences by best similarity,
        which is where "edited" and "cosmetic" come from.
        """
        old_keys = [u.key for u in old_units]
        new_keys = [u.key for u in new_units]
        matcher = SequenceMatcher(None, old_keys, new_keys, autojunk=False)

        aligned: list[tuple[ChangeKind, Unit | None, Unit | None]] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for offset in range(i2 - i1):
                    old = old_units[i1 + offset]
                    new = new_units[j1 + offset]
                    kind = (
                        ChangeKind.UNCHANGED
                        if old.text == new.text
                        else ChangeKind.COSMETIC
                    )
                    aligned.append((kind, old, new))
                continue
            aligned.extend(
                self._pair_block(
                    old_units[i1:i2],
                    new_units[j1:j2],
                    backend,
                )
            )
        return aligned

    def _pair_block(
        self,
        removed: Sequence[Unit],
        added: Sequence[Unit],
        backend: Backend,
    ) -> list[tuple[ChangeKind, Unit | None, Unit | None]]:
        """Greedily pair the strongest removed/added candidates in a block."""
        if not removed:
            return [(ChangeKind.ADDED, None, u) for u in added]
        if not added:
            return [(ChangeKind.REMOVED, u, None) for u in removed]

        candidates: list[tuple[float, int, int]] = []
        for i, old in enumerate(removed):
            for j, new in enumerate(added):
                score = backend.score(old.text, new.text)
                if score >= self.min_similarity:
                    candidates.append((score, i, j))
        candidates.sort(reverse=True)

        paired_old: dict[int, int] = {}
        paired_new: dict[int, int] = {}
        for _, i, j in candidates:
            if i in paired_old or j in paired_new:
                continue
            paired_old[i] = j
            paired_new[j] = i

        block: list[tuple[ChangeKind, Unit | None, Unit | None]] = []
        # Walk in document order so the diff reads naturally.
        pending_added = [j for j in range(len(added)) if j not in paired_new]
        for i, old in enumerate(removed):
            if i in paired_old:
                j = paired_old[i]
                block.append((ChangeKind.EDITED, old, added[j]))
            else:
                block.append((ChangeKind.REMOVED, old, None))
        tail = [(ChangeKind.ADDED, None, added[j]) for j in pending_added]
        return _interleave_by_offset(block, tail, len(removed))

    @staticmethod
    def _pair_similarity(old: Unit | None, new: Unit | None, backend: Backend) -> float:
        if old is None or new is None:
            return 0.0
        if old.text == new.text:
            return 1.0
        return backend.score(old.text, new.text)


def _interleave_by_offset(
    block: list[tuple[ChangeKind, Unit | None, Unit | None]],
    tail: list[tuple[ChangeKind, Unit | None, Unit | None]],
    split: int,
) -> list[tuple[ChangeKind, Unit | None, Unit | None]]:
    """Append unattached additions after the removals they followed.

    Keeps output order stable enough to read top-to-bottom without pretending
    to know an exact position for pure insertions.
    """
    if not tail:
        return block
    head = block[:split]
    rest = block[split:]
    return head + rest + tail


def compare(
    old_text: str,
    new_text: str,
    min_similarity: float = 0.5,
    backend_name: str | None = None,
) -> Report:
    """Convenience one-liner around :class:`Comparer`."""
    return Comparer(
        min_similarity=min_similarity,
        backend_name=backend_name,
    ).compare(old_text, new_text)
