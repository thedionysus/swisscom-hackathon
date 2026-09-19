from swiss_grounding.locations.fuzzy import edit_distance, tokens_covered


def test_edit_distance():
    assert edit_distance("winterthur", "winterthurr") == 1
    assert edit_distance("zurich", "zurichsee") == 3


def test_tokens_covered_requires_every_input_token():
    assert tokens_covered("Winterthur", "Winterthur (ZH)")
    assert tokens_covered("Winterthurr", "Winterthur (ZH)")          # one edit on a long token
    assert not tokens_covered("Zürich Oberland", "Zürich (ZH)")      # oberland unaccounted for
    assert not tokens_covered("Zurich Airport", "Zürich (ZH)")
    assert not tokens_covered("Nowhere", "Nidwalden (NW)")
    assert not tokens_covered("Wil", "Wila (ZH)")                    # short tokens must match exactly
