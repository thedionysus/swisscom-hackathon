import hashlib
import re
from collections.abc import Sequence
from typing import Protocol

import numpy as np

TOKEN_RE = re.compile(r"[a-zA-Z0-9äöüéèàç]+")


class Embedder(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]: ...


class FakeEmbedder:
    """Deterministic bag-of-hashed-tokens embedding. For tests and offline demos only."""

    def __init__(self, dim: int):
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[index] += sign
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, dim: int):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        arr = self._model.encode(list(texts), normalize_embeddings=True)
        return [np.asarray(row, dtype=np.float32) for row in arr]


def build_embedder(backend: str, model_name: str, dim: int) -> Embedder:
    if backend == "fake":
        return FakeEmbedder(dim=dim)
    if backend == "sentence_transformers":
        return SentenceTransformerEmbedder(model_name=model_name, dim=dim)
    raise ValueError(f"unknown embedding backend: {backend}")
