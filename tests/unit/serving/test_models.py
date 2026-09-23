from datetime import date

import pytest

from swiss_grounding.serving.models import (
    LANGS,
    MAX_LOCATIONS,
    SearchRequest,
    overall_status,
)


def test_request_rejects_more_than_three_places():
    with pytest.raises(ValueError, match="at most 3"):
        SearchRequest(question="x", locations=("Bern", "Lausanne", "Chur", "Scuol"))


def test_request_drops_unknown_translation_languages():
    r = SearchRequest(question="x", translations={"fr": "bonjour", "xx": "?", "de": " "})
    assert r.translations == {"fr": "bonjour"}


def test_overall_status_is_results_when_any_place_has_results():
    assert overall_status(("no_evidence", "results")) == "results"


def test_overall_status_prefers_outside_scope_over_no_evidence():
    assert overall_status(("no_evidence", "outside_scope")) == "outside_scope"


def test_constants():
    assert LANGS == ("de", "fr", "it", "en", "rm")
    assert MAX_LOCATIONS == 3
    assert SearchRequest(question="q", as_of=date(2026, 1, 1)).limit == 8
