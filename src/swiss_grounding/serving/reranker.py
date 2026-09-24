"""The cross-encoder that scores (question, passage) pairs."""
import re
from collections.abc import Sequence
from typing import Protocol

BREADCRUMB_SEPARATOR = " › "
TOKEN = re.compile(r"[\wà-ÿ]{3,}|\d+[a-z]?", re.IGNORECASE)


class Reranker(Protocol):
    name: str

    def score(self, question: str, passages: Sequence[str]) -> list[float]: ...


def detect_device() -> str:
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def choose_model(setting: str, *, gpu_model: str, cpu_model: str, device: str) -> str:
    if setting != "auto":
        return setting
    return cpu_model if device == "cpu" else gpu_model


MARKDOWN = re.compile(r"[*_#`]+")
SPACES = re.compile(r"[ \t]{2,}")


def passage_text(breadcrumb: Sequence[str], text: str) -> str:
    """Breadcrumb and text as the reranker reads them. Markdown emphasis is stripped: on real pages
    ("**12** **mois**") it lowered the score of the right passage (docs/EVALUATION.md)."""
    crumb = BREADCRUMB_SEPARATOR.join(breadcrumb)
    body = SPACES.sub(" ", MARKDOWN.sub("", text)).strip()
    return f"{crumb}\n{body}" if crumb else body


class CrossEncoderReranker:
    def __init__(self, model: str, *, device: str, max_tokens: int):
        import torch
        from sentence_transformers import CrossEncoder
        self.name = model
        self._activation = torch.nn.Sigmoid()
        self._model = CrossEncoder(model, device=device, max_length=max_tokens)
        if device != "cpu":
            self._model.model.half()

    def score(self, question: str, passages: Sequence[str]) -> list[float]:
        if not passages:
            return []
        scores = self._model.predict([(question, p) for p in passages], batch_size=16,
                                     activation_fn=self._activation)
        return [float(s) for s in scores]


class OverlapReranker:
    """Deterministic stand-in for tests: share of question tokens found in the passage."""
    name = "overlap"

    def score(self, question: str, passages: Sequence[str]) -> list[float]:
        wanted = {t.lower() for t in TOKEN.findall(question)}
        if not wanted:
            return [0.0 for _ in passages]
        return [len(wanted & {t.lower() for t in TOKEN.findall(p)}) / len(wanted) for p in passages]
