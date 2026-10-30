"""Deterministic, dependency-free text similarity.

Two complementary signals are combined:

``tfidf``
    Word-level cosine over the whole corpus, so rare words dominate. Good at
    "same sentence, one number changed".

``char3``
    Cosine over hashed character trigrams. Good at morphology and reflowed
    wording ("pay" / "payment", "Supplier" / "the Supplier's").

The final score is ``max`` of the two. No model download, no network, no API
key - results are bit-for-bit reproducible, which is what you want in a
regression gate. An optional embedding backend lives in
:mod:`clausedrift.backends`.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from collections.abc import Iterable

_TOKEN_RE = re.compile(r"\$?\d[\d,.]*|[a-z][a-z'\-]*")

STOPWORDS = frozenset(
    """
    a an the and or but if then than that this these those there here
    of to in on at by for with from as into onto over under about after
    is are was were be been being am do does did doing done have has had
    it its their theirs our ours your yours his her hers they them
    we us you he she i me my mine who whom which what when where why how
    so such only own same too very can will just should now
    shall may might must would could also any all both each other more most
    """.split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens with stopwords removed.

    Negations (``not``, ``no``, ``nor``) are deliberately kept: dropping them
    made "may terminate" and "may not terminate" look identical.
    """
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def _l2(vector: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(v * v for v in vector.values()))
    if norm == 0.0:
        return {}
    return {k: v / norm for k, v in vector.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(key, 0.0) for key, weight in a.items())


def char_ngrams(text: str, n: int = 3) -> list[str]:
    """Character n-grams over whitespace-squashed text."""
    squashed = " ".join(text.lower().split())
    if len(squashed) < n:
        return [squashed] if squashed else []
    return [squashed[i : i + n] for i in range(len(squashed) - n + 1)]


def _hash_bucket(gram: str, dimensions: int) -> str:
    digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
    return str(int.from_bytes(digest, "big") % dimensions)


class Similarity:
    """Corpus-aware similarity scorer with memoisation.

    Build one instance per comparison: the IDF table comes from both
    documents, so scores are relative to the pair being compared.
    """

    def __init__(self, corpus: Iterable[str], dimensions: int = 4096) -> None:
        documents = [d for d in corpus if d]
        self.dimensions = dimensions
        self.size = len(documents)
        self._tfidf: dict[str, dict[str, float]] = {}
        self._chars: dict[str, dict[str, float]] = {}
        self._pairs: dict[tuple[str, str], float] = {}

        df: Counter[str] = Counter()
        for document in documents:
            df.update(set(tokenize(document)))
        total = max(1, self.size)
        # Unseen terms get maximum weight so vocabulary changes cost something.
        self._unseen = math.log(1.0 + total) + 1.0
        self.idf = {
            term: math.log((1.0 + total) / (1.0 + count)) + 1.0
            for term, count in df.items()
        }

    def tfidf_vector(self, text: str) -> dict[str, float]:
        cached = self._tfidf.get(text)
        if cached is not None:
            return cached
        counts = Counter(tokenize(text))
        vector = {
            term: (1.0 + math.log(count)) * self.idf.get(term, self._unseen)
            for term, count in counts.items()
        }
        normed = _l2(vector)
        self._tfidf[text] = normed
        return normed

    def char_vector(self, text: str) -> dict[str, float]:
        cached = self._chars.get(text)
        if cached is not None:
            return cached
        counts: Counter[str] = Counter(
            _hash_bucket(gram, self.dimensions) for gram in char_ngrams(text)
        )
        normed = _l2(dict(counts))
        self._chars[text] = normed
        return normed

    def score(self, a: str, b: str) -> float:
        """Similarity in ``[0, 1]``; ``1.0`` means identical."""
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0
        key = (a, b) if a <= b else (b, a)
        cached = self._pairs.get(key)
        if cached is not None:
            return cached
        word = _cosine(self.tfidf_vector(a), self.tfidf_vector(b))
        char = _cosine(self.char_vector(a), self.char_vector(b))
        result = round(max(word, char), 6)
        self._pairs[key] = result
        return result
