"""Tests for the similarity scorer."""

from __future__ import annotations

import pytest

from clausedrift.similarity import Similarity, char_ngrams, tokenize


class TestTokenize:
    def test_stopwords_removed(self):
        assert tokenize("The fee is due") == ["fee", "due"]

    def test_numbers_kept(self):
        assert "50" in tokenize("fee is 50 dollars")

    def test_lowercased(self):
        assert tokenize("FEE") == ["fee"]


class TestCharNgrams:
    def test_count(self):
        assert len(char_ngrams("abcd", n=3)) == 2

    def test_short_text(self):
        assert char_ngrams("ab", n=3) == ["ab"]

    def test_empty(self):
        assert char_ngrams("", n=3) == []


class TestSimilarity:
    @pytest.fixture()
    def scorer(self):
        corpus = [
            "The fee is $50 per month.",
            "The fee is $75 per month.",
            "The bakery opens at dawn.",
        ]
        return Similarity(corpus)

    def test_identical_is_one(self, scorer):
        assert scorer.score("same text", "same text") == 1.0

    def test_number_change_scores_high(self, scorer):
        assert scorer.score("The fee is $50 per month.", "The fee is $75 per month.") > 0.7

    def test_unrelated_scores_low(self, scorer):
        assert scorer.score("The fee is $50 per month.", "The bakery opens at dawn.") < 0.3

    def test_symmetric(self, scorer):
        a, b = "The fee is $50 per month.", "The fee is $75 per month."
        assert scorer.score(a, b) == scorer.score(b, a)

    def test_bounded(self, scorer):
        for score in (
            scorer.score("a", "b"),
            scorer.score("", "b"),
            scorer.score("The fee is $50 per month.", "The bakery opens at dawn."),
        ):
            assert 0.0 <= score <= 1.0

    def test_empty_inputs(self, scorer):
        assert scorer.score("", "anything") == 0.0

    def test_memoisation_returns_same(self, scorer):
        assert scorer.score("a b c", "a b d") == scorer.score("a b c", "a b d")


def test_negation_is_not_ignored():
    sim = Similarity(["The Buyer may terminate.", "The Buyer may not terminate."])
    assert "not" in tokenize("The Buyer may not terminate.")
    assert sim.score("The Buyer may terminate.", "The Buyer may not terminate.") < 1.0


def test_negation_change_is_an_edit():
    from clausedrift import compare

    report = compare("The Buyer may terminate.", "The Buyer may not terminate.")
    assert report.changes[0].kind.value == "edited"
    assert report.changes[0].similarity < 1.0
    assert report.drift_score > 0


def test_neither_vs_either_not_identical():
    sim = Similarity(["Either party may terminate.", "Neither party may terminate."])
    assert sim.score("Either party may terminate.", "Neither party may terminate.") < 1.0
