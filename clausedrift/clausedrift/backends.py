"""Optional similarity backends.

The default :class:`clausedrift.similarity.Similarity` needs nothing but the
standard library. If you install ``sentence-transformers`` and set
``CLAUSEDRIFT_BACKEND=embedding``, you get true semantic matching instead
(paraphrases score high even with no shared vocabulary).

Both backends expose the same :meth:`score` signature, so the engine does not
care which one it was handed.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Protocol

from .similarity import Similarity


class Backend(Protocol):
    """Anything with ``score(a, b) -> float in [0, 1]``."""

    def score(self, a: str, b: str) -> float: ...


class EmbeddingSimilarity:
    """Cosine similarity over sentence-transformer embeddings.

    Raises:
        RuntimeError: if ``sentence-transformers`` is not installed.
    """

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(
        self,
        corpus: Iterable[str],
        model_name: str | None = None,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer, util
        except ImportError as exc:  # pragma: no cover - optional path
            raise RuntimeError(
                "The embedding backend needs sentence-transformers. "
                "Install it with: pip install 'clausedrift[semantic]'"
            ) from exc

        self._util = util
        self.model = SentenceTransformer(model_name or self.DEFAULT_MODEL)
        self._texts: dict[str, object] = {}
        for text in corpus:
            if text and text not in self._texts:
                self._texts[text] = self.model.encode(text, convert_to_tensor=True)

    def _embed(self, text: str):
        if text not in self._texts:
            self._texts[text] = self.model.encode(text, convert_to_tensor=True)
        return self._texts[text]

    def score(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0
        value = self._util.cos_sim(self._embed(a), self._embed(b)).item()
        return max(0.0, min(1.0, round(float(value), 6)))


def build_backend(
    corpus: Iterable[str],
    name: str | None = None,
) -> Backend:
    """Pick a backend by name, defaulting to ``CLAUSEDRIFT_BACKEND`` or tfidf."""
    choice = (name or os.getenv("CLAUSEDRIFT_BACKEND") or "tfidf").strip().lower()
    documents = list(corpus)
    if choice in {"embedding", "embeddings", "semantic", "sbert"}:
        return EmbeddingSimilarity(documents)
    if choice not in {"tfidf", "default", "lexical"}:
        raise ValueError(
            f"Unknown backend {choice!r}. Use 'tfidf' or 'embedding'."
        )
    return Similarity(documents)
