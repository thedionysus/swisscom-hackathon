"""Quotas for the golden set (Task 25). This is the first batch of ~40 probes; the quotas below check
this batch only. They grow towards the plan's ~150-probe targets (evals/golden/*.yaml quotas table) in
later batches, so these thresholds are intentionally looser than the final ones."""
from collections import Counter

from swiss_grounding.evals.golden_models import load_golden


def test_golden_set_loads_and_meets_first_batch_quotas():
    golden = load_golden()
    assert len(golden.probes) >= 38

    statuses = Counter(p.expect.status for p in golden.probes)
    assert statuses["outside_scope"] >= 4
    assert statuses["needs_location"] >= 3

    assert sum(1 for p in golden.probes if p.expect.place_statuses) >= 2

    languages = Counter(p.language for p in golden.probes)
    assert languages["rm"] >= 3

    holdout = sum(1 for p in golden.probes if p.split == "holdout")
    assert 0.2 <= holdout / len(golden.probes) <= 0.35
