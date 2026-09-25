from swiss_grounding.evals.golden_analysis import (
    abstention,
    compare,
    confusion,
    headline,
    slices,
)
from swiss_grounding.evals.golden_runner import ProbeOutcome, leakage


def _o(pid, want, got, **kw):
    base = {"probe_id": pid, "expected_status": want, "status": got, "keys": (), "recall": None, "precision": None,
                "ndcg": None}
    return ProbeOutcome(**{**base, **kw})


def test_leakage_counts_citations_off_the_place_path():
    assert leakage([("CH", "CH-ZH", "CH-BE")], [("CH", "CH-ZH")]) == 1 / 3
    assert leakage([("CH-BE",), ("CH-BE",)], [("CH", "CH-ZH"), ("CH", "CH-BE")]) == 0.5
    assert leakage([()], [("CH",)]) is None


def test_abstention_rates():
    outs = [_o("a", "results", "results"), _o("b", "results", "no_evidence"),
            _o("c", "outside_scope", "results"), _o("d", "outside_scope", "outside_scope"),
            _o("e", "no_evidence", "no_evidence")]
    ab = abstention(outs)
    assert ab["false_answer_rate"] == (1, 3)
    assert ab["false_abstention_rate"] == (1, 2)


def test_confusion_matrix_counts_expected_by_got():
    outs = [_o("a", "results", "results"), _o("b", "results", "no_evidence"), _o("c", "results", "results")]
    assert confusion(outs) == {"results": {"results": 2, "no_evidence": 1}}


def test_headline_carries_ci_and_n():
    outs = [_o("a", "results", "results", recall=1.0), _o("b", "results", "no_evidence", recall=0.0)]
    h = headline(outs)
    assert h["status_accuracy"].value == 0.5 and h["status_accuracy"].n == 2
    assert h["status_accuracy"].ci[0] < 0.5 < h["status_accuracy"].ci[1]
    assert h["recall@5"].n == 2


def test_slices_group_by_attribute():
    outs = [_o("a", "results", "results", language="de"), _o("b", "results", "no_evidence", language="fr")]
    by_lang = slices(outs)["language"]
    assert by_lang["de"]["status_accuracy"].value == 1.0
    assert by_lang["fr"]["status_accuracy"].n == 1


def test_compare_reports_deltas_and_flips():
    old = {"summary": {"recall@5": 0.5}, "outcomes": [
        {"probe_id": "a", "status": "results", "expected_status": "results"},
        {"probe_id": "b", "status": "no_evidence", "expected_status": "results"}]}
    new = {"summary": {"recall@5": 0.75}, "outcomes": [
        {"probe_id": "a", "status": "no_evidence", "expected_status": "results"},
        {"probe_id": "b", "status": "results", "expected_status": "results"}]}
    c = compare(old, new)
    assert c["deltas"]["recall@5"] == (0.5, 0.75, 0.25)
    assert c["pass_to_fail"] == ["a"] and c["fail_to_pass"] == ["b"]
