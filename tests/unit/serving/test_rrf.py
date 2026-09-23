from swiss_grounding.serving.rrf import RRF_K, fuse, select_with_pool, select_with_quota


def test_fuse_sums_reciprocal_ranks_and_records_arms():
    fused = fuse({"dense": ["a", "b"], "sparse": ["b", "c"]})
    assert [key for key, _, _ in fused] == ["b", "a", "c"]
    score_b = 1 / (RRF_K + 2) + 1 / (RRF_K + 1)
    assert abs(fused[0][1] - score_b) < 1e-12
    assert fused[0][2] == frozenset({"dense", "sparse"})


def test_fuse_is_stable_for_ties():
    fused = fuse({"x": ["a"], "y": ["b"]})
    assert [key for key, _, _ in fused] == ["a", "b"]


def test_quota_pulls_local_items_into_the_top_n():
    order = ["f1", "f2", "f3", "l1", "f4", "l2"]
    chosen = select_with_quota(order, is_local=lambda k: k.startswith("l"), n=4, quota=2)
    assert chosen == ["f1", "f2", "l1", "l2"]


def test_quota_does_not_invent_local_items():
    chosen = select_with_quota(["f1", "f2", "f3"], is_local=lambda k: False, n=2, quota=2)
    assert chosen == ["f1", "f2"]


def test_quota_larger_than_n_never_exceeds_n():
    order = ["l1", "l2", "l3", "f1"]
    chosen = select_with_quota(order, is_local=lambda k: k.startswith("l"), n=2, quota=5)
    assert chosen == ["l1", "l2"]


def test_pool_fills_the_quota_from_its_own_order_then_the_main_order():
    chosen = select_with_pool(["f1", "f2", "l2", "f3"], ["l1", "l2"], n=3, quota=2)
    assert chosen == ["l1", "l2", "f1"]


def test_pool_quota_is_capped_by_n():
    assert select_with_pool(["f1"], ["l1", "l2", "l3"], n=2, quota=3) == ["l1", "l2"]
