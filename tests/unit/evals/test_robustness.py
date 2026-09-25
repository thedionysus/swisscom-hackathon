from swiss_grounding.evals.golden_models import GoldenProbe, GoldenSet
from swiss_grounding.evals.robustness import Hit, compare, run_robustness


def results_probe(pid="p-1", question="Wie lange ist die Kündigungsfrist?") -> GoldenProbe:
    return GoldenProbe.model_validate({
        "id": pid, "question": question, "language": "de", "area": "law", "level": "federal", "split": "dev",
        "expect": {"status": "results", "sources": ["art_266_c"], "key_fact": "drei Monate"}})


def test_compare_measures_agreement():
    base = Hit("results", ("https://a#art_266_c", "https://b", "https://c"))
    var = Hit("results", ("https://b", "https://a#art_266_c", "https://d"))
    m = compare(base, var, expected=("art_266_c",))
    assert m.status_agrees and not m.top1_agrees
    assert m.jaccard == 2 / 4 and m.recall == 1.0


def test_jaccard_of_two_empty_lists_is_one():
    assert compare(Hit("no_evidence", ()), Hit("no_evidence", ()), expected=("x",)).jaccard == 1.0


def test_run_robustness_perturbs_only_results_probes_and_averages():
    other = GoldenProbe.model_validate({
        "id": "n-1", "question": "Wie hoch ist die Hundesteuer?", "language": "de", "area": "none",
        "level": "none", "split": "dev", "expect": {"status": "needs_location"}})
    golden = GoldenSet(version="v", probes=(results_probe(), other))
    asked = []

    def search(question, locations):
        asked.append(question)
        return Hit("results", ("https://a#art_266_c",)) if question == golden.probes[0].question \
            else Hit("no_evidence", ())
    report = run_robustness(golden, search, split="all", seed=1)
    assert "Wie hoch ist die Hundesteuer?" not in asked
    assert report.overall["status_agreement"] == 0.0
    assert report.overall["recall@5"] == 0.0 and report.baseline_recall == 1.0
    assert set(report.per_perturbation) >= {"lowercase", "typo"}
