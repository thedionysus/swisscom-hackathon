from swiss_grounding.retrieval.search import reciprocal_rank_fusion


def test_rrf_combines_ranks():
    fused = reciprocal_rank_fusion(dense=[10, 20, 30], lexical=[20, 40], k=60)
    ids = [chunk_id for chunk_id, _ in fused]
    assert ids[0] == 20                     # appears in both lists
    assert set(ids) == {10, 20, 30, 40}
    scores = dict(fused)
    assert scores[20] == 1 / (60 + 2) + 1 / (60 + 1)


def test_rrf_reports_ranks():
    fused = reciprocal_rank_fusion(dense=[1], lexical=[2], k=60, with_ranks=True)
    assert fused == [(1, 1 / 61, 1, None), (2, 1 / 61, None, 1)]
