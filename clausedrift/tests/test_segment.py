"""Tests for segmentation and normalisation."""

from __future__ import annotations

from clausedrift.segment import segment, split_paragraphs, split_sentences
from clausedrift.textutil import content_key, normalize_ws, truncate


class TestNormalize:
    def test_smart_quotes_become_ascii(self):
        assert normalize_ws("\u201cThe Supplier\u2019s\u201d duty") == '"The Supplier\'s" duty'

    def test_dashes_and_nbsp(self):
        assert normalize_ws("A\u2013B\u00a0C") == "A-B C"

    def test_collapses_tabs_and_newlines_spaces(self):
        assert normalize_ws("a \t  b") == "a b"

    def test_content_key_ignores_case_and_punctuation(self):
        assert content_key("The Fee is $50.") == content_key("the fee is 50")

    def test_content_key_keeps_digits(self):
        assert content_key("fee 50") != content_key("fee 75")

    def test_truncate_adds_ellipsis(self):
        out = truncate("x" * 200, limit=10)
        assert len(out) == 10 and out.endswith("\u2026")

    def test_truncate_short_text_unchanged(self):
        assert truncate("short", limit=10) == "short"


class TestParagraphs:
    def test_blank_line_splits(self):
        assert split_paragraphs("One.\n\nTwo.") == ["One.", "Two."]

    def test_soft_wraps_join(self):
        assert split_paragraphs("One line\ncontinues here.") == ["One line continues here."]

    def test_bullet_markers_stripped(self):
        assert split_paragraphs("- alpha\n- beta") == ["alpha beta"]

    def test_numbered_markers_stripped(self):
        assert split_paragraphs("1. alpha\n2) beta") == ["alpha beta"]


class TestSentences:
    def test_basic_split(self):
        assert split_sentences("A b. C d.") == ["A b.", "C d."]

    def test_abbreviation_not_split(self):
        out = split_sentences("Dr. Smith signed. It was approved.")
        assert out == ["Dr. Smith signed.", "It was approved."]

    def test_initial_not_split(self):
        assert split_sentences("J. Doe agreed.") == ["J. Doe agreed."]

    def test_question_and_exclamation(self):
        assert len(split_sentences("Really? Yes! Fine.")) == 3

    def test_single_sentence(self):
        assert split_sentences("No boundary here") == ["No boundary here"]


class TestSegment:
    def test_empty_document(self):
        assert segment("") == []
        assert segment("   \n\n  ") == []

    def test_indices_are_sequential(self):
        units = segment("One. Two. Three.")
        assert [u.index for u in units] == [0, 1, 2]

    def test_paragraph_is_tagged(self):
        units = segment("A one. A two.\n\nB one.")
        assert [u.paragraph for u in units] == [0, 0, 1]

    def test_keys_are_normalised(self):
        units = segment("The Fee is  $50.")
        assert units[0].key == "the fee is 50"
        assert units[0].text == "The Fee is $50."
