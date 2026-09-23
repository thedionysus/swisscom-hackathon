import pytest

from swiss_grounding.app import load_location_tree
from swiss_grounding.db.connection import connect
from swiss_grounding.serving.coverage import coverage_rows
from tests.integration.serving.corpus_fixture import add_doc

pytestmark = pytest.mark.integration


def test_counts_current_documents_per_extent_on_the_path(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="a", lang="de", text="x")
        add_doc(conn, group="b", lang="de", text="y", extent="CH-ZH-261", source="zh")
        tree = load_location_tree(conn)
        rows = coverage_rows(conn, tree, ("CH", "CH-ZH", "CH-ZH-261"))
    assert [(r.extent_id, r.documents) for r in rows] == [("CH", 1), ("CH-ZH", 0), ("CH-ZH-261", 1)]
