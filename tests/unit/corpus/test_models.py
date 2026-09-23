from datetime import date

from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, content_hash


def _doc(**kw):
    base = dict(source_id="s", url="https://x", language="de", work_key="k", title="Hundegesetz",
                sections=(ParsedSection(align_key="art_1", breadcrumb=("Hundegesetz", "Art. 1"), anchor="art_1",
                                        text="Zweck"),))
    base.update(kw)
    return ParsedDocument(**base)


def test_content_hash_changes_with_title_and_breadcrumb():
    a = content_hash(_doc())
    assert content_hash(_doc(title="Hundeverordnung")) != a
    changed = ParsedSection(align_key="art_1", breadcrumb=("Hundegesetz", "Art. 1 Zweck"), anchor="art_1", text="Zweck")
    assert content_hash(_doc(sections=(changed,))) != a


def test_content_hash_ignores_status_but_not_validity():
    a = content_hash(_doc())
    assert content_hash(_doc(status="scheduled")) == a
    assert content_hash(_doc(valid_from=date(2026, 1, 1))) != a
