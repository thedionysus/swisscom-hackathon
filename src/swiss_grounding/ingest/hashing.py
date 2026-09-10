import hashlib

from swiss_grounding.ingest.models import FetchedDocument


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def content_hash(doc: FetchedDocument) -> str:
    """Hash of the original section texts only; title and metadata changes do not count."""
    return text_hash("\n␞".join(s.text for s in doc.sections))
