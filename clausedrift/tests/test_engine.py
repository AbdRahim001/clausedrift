"""End-to-end tests for the comparison engine."""

from __future__ import annotations

from clausedrift import ChangeKind, Comparer, compare

IDENTICAL = "The fee is $50 per month. Payment is due on the first day."


class TestIdentical:
    def test_zero_drift(self):
        report = compare(IDENTICAL, IDENTICAL)
        assert report.drift_score == 0.0
        assert report.similarity == 100.0
        assert report.verdict() == "identical"

    def test_all_units_unchanged(self):
        report = compare(IDENTICAL, IDENTICAL)
        assert all(c.kind is ChangeKind.UNCHANGED for c in report.changes)
        assert report.old_units == report.new_units == 2


class TestEdit:
    def test_number_change_is_one_edit(self):
        report = compare("The fee is $50 per month.", "The fee is $75 per month.")
        assert report.substantive == 1
        change = report.changes[0]
        assert change.kind is ChangeKind.EDITED
        assert change.similarity > 0.7
        assert "$50" in change.old.text and "$75" in change.new.text

    def test_case_only_change_is_cosmetic(self):
        report = compare(
            "The party shall not be liable.",
            "the party shall not be liable",
        )
        assert report.changes[0].kind is ChangeKind.COSMETIC
        assert report.drift_score == 0.0

    def test_cosmetic_does_not_count_as_drift(self):
        report = compare("Notice is given.", "Notice is given!")
        assert report.drift_score == 0.0
        assert report.substantive == 0

    def test_threshold_controls_pairing(self):
        old = "The supplier must deliver the goods by Friday."
        new = "The bakery opens at dawn on Tuesday."
        lenient = compare(old, new, min_similarity=0.0)
        strict = compare(old, new, min_similarity=0.9)
        assert lenient.changes[0].kind is ChangeKind.EDITED
        kinds = {c.kind for c in strict.changes}
        assert kinds == {ChangeKind.REMOVED, ChangeKind.ADDED}


class TestInsertDelete:
    def test_added_sentence(self):
        report = compare(
            "Alpha one. Beta two.",
            "Alpha one. Beta two. Gamma three.",
        )
        kinds = [c.kind for c in report.changes]
        assert ChangeKind.ADDED in kinds
        assert report.new_units == 3

    def test_removed_sentence(self):
        report = compare(
            "Alpha one. Beta two. Gamma three.",
            "Alpha one. Beta two.",
        )
        kinds = [c.kind for c in report.changes]
        assert ChangeKind.REMOVED in kinds

    def test_full_rewrite_has_high_drift(self):
        report = compare(
            "The supplier shall indemnify the buyer against all claims.",
            "A completely different statement about cafeteria opening hours.",
        )
        assert report.drift_score > 50
        assert report.verdict() in {"significant changes", "rewritten"}


class TestEdgeCases:
    def test_both_empty(self):
        report = compare("", "")
        assert report.changes == []
        assert report.drift_score == 0.0

    def test_added_from_empty(self):
        report = compare("", "One sentence here.")
        assert report.changes[0].kind is ChangeKind.ADDED
        assert report.drift_score == 100.0

    def test_removed_to_empty(self):
        report = compare("One sentence here.", "")
        assert report.changes[0].kind is ChangeKind.REMOVED

    def test_long_document_is_stable(self):
        old = " ".join(f"Sentence number {i} about clause {i}." for i in range(200))
        new = old.replace("Sentence number 100", "Sentence number 999")
        report = compare(old, new)
        assert report.old_units == 200
        assert report.substantive == 1
        assert report.drift_score < 2

    def test_report_dict_is_serialisable(self):
        report = compare("A b.", "A c.")
        payload = report.as_dict()
        assert set(payload) >= {"drift_score", "changes", "counts", "verdict"}
        assert isinstance(payload["changes"][0]["kind"], str)

    def test_invalid_threshold_rejected(self):
        import pytest

        with pytest.raises(ValueError):
            Comparer(min_similarity=1.5)
