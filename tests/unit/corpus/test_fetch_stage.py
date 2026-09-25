from collections import Counter
from contextlib import nullcontext
from datetime import UTC, datetime

from swiss_grounding.corpus import fetch_stage
from swiss_grounding.corpus.models import ConnectorResult, SourceSpec

SPEC = SourceSpec(id="x", name="X", publisher="X", authority="official_info", level="municipal",
                  extent_id="CH-BE-351", connector="html", tier=1, languages=("de",), config={})


def test_skipped_links_are_tallied_per_reason(monkeypatch):
    """#11: what a connector found but deliberately did not fetch shows in the fetch report."""
    monkeypatch.setattr(fetch_stage, "connect", lambda url: nullcontext(object()))
    monkeypatch.setattr(fetch_stage, "upsert_source", lambda conn, spec: None)
    monkeypatch.setattr(fetch_stage, "known_state", lambda conn, source_id: {})
    monkeypatch.setattr(fetch_stage, "_persist_result", lambda *args: None)

    class Connector:
        def run(self, spec, known):
            return ConnectorResult(skipped=(("https://x.ch/a.docx", ".docx"), ("https://x.ch/b.docx", ".docx"),
                                            ("https://x.ch/c.pdf", "max_pdfs")))

    tally = fetch_stage._run_source("db", SPEC, {"html": Connector()}, None, now=lambda: datetime.now(tz=UTC))
    assert tally == Counter({"skipped[.docx]": 2, "skipped[max_pdfs]": 1})
