from swiss_grounding.evals.consistency import Answer, run_consistency
from swiss_grounding.evals.golden_models import GoldenProbe, GoldenSet


def probe(pid, lang, group=None) -> GoldenProbe:
    return GoldenProbe.model_validate({
        "id": pid, "question": f"question {pid}", "language": lang, "area": "law", "level": "federal",
        "split": "dev", "group": group, "expect": {"status": "results", "sources": ["x"], "key_fact": "y"}})


def test_groups_agree_on_status_and_translation_group():
    golden = GoldenSet(version="v", probes=(probe("a-de", "de", "a"), probe("a-it", "it", "a"),
                                            probe("b-de", "de", "b"), probe("b-fr", "fr", "b"),
                                            probe("solo", "de")))
    answers = {"question a-de": Answer("results", "g1#art_94"), "question a-it": Answer("results", "g1#art_94"),
               "question b-de": Answer("results", "g2"), "question b-fr": Answer("no_evidence", None)}
    report = run_consistency(golden, lambda q, locs: answers[q], split="all")
    assert [g.group for g in report.groups] == ["a", "b"]
    assert report.groups[0].status_agrees and report.groups[0].top_agrees
    assert not report.groups[1].status_agrees and not report.groups[1].top_agrees
    assert report.summary == {"groups": 2, "status_agreement": 0.5, "top_citation_agreement": 0.5}


def test_a_group_of_one_is_ignored():
    golden = GoldenSet(version="v", probes=(probe("a-de", "de", "a"),))
    assert run_consistency(golden, lambda q, locs: Answer("results", "g"), split="all").groups == ()
