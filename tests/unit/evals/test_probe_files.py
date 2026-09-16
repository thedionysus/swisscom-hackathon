from collections import Counter

from swiss_grounding.evals.probe_loader import PROBE_DIR, load_all_probes

FAILURE_CLASSES = {
    "jurisdiction_confusion", "authority_hierarchy", "temporal_misapplication",
    "entity_substitution", "silent_under_coverage",
}


def test_probe_dir_loads():
    probes = load_all_probes(PROBE_DIR)
    assert len(probes) >= 20


def test_city_tier_has_twenty_probes():
    tiers = Counter(t for t, _ in load_all_probes(PROBE_DIR))
    assert tiers["city"] == 20


def test_every_failure_class_is_probed():
    classes = {p.failure_class for _, p in load_all_probes(PROBE_DIR)}
    assert FAILURE_CLASSES <= classes


def test_every_probe_has_a_note_when_red():
    for _, p in load_all_probes(PROBE_DIR):
        if p.status == "red":
            assert p.note, f"{p.id} is red but has no note explaining why"
