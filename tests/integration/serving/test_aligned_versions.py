import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.serving.groups import aligned_versions
from tests.integration.serving.corpus_fixture import add_doc

pytestmark = pytest.mark.integration


def test_loads_every_live_version_of_the_keys(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="g", lang="de", text="Frist", align="art_1")
        add_doc(conn, group="g", lang="fr", text="Délai", align="art_1")
        add_doc(conn, group="g", lang="it", text="Termine", align="art_2")
        versions = aligned_versions(conn, [("g", "art_1")], as_of=None)
    assert sorted(v.language for v in versions[("g", "art_1")]) == ["de", "fr"]
