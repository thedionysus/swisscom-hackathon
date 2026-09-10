from swiss_grounding.ingest.hashing import content_hash, text_hash
from swiss_grounding.ingest.models import FetchedDocument, Section


def doc(*texts):
    return FetchedDocument(
        source_id="s", url="https://x/y", title="T", language="de",
        sections=tuple(Section(heading_path=f"H{i}", anchor=None, text=t) for i, t in enumerate(texts)),
    )


def test_content_hash_depends_on_section_text_only():
    a = doc("one", "two")
    b = FetchedDocument(**{**a.__dict__, "title": "Other title"})
    assert content_hash(a) == content_hash(b)
    assert content_hash(a) != content_hash(doc("one", "three"))


def test_text_hash_is_sha256_hex():
    assert len(text_hash("abc")) == 64
    assert text_hash("abc") == text_hash("abc")


def test_fetched_document_is_frozen():
    import pytest

    with pytest.raises(Exception):  # noqa: B017
        doc("x").title = "y"  # type: ignore[misc]
