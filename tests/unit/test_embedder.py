import numpy as np

from swiss_grounding.retrieval.embedder import FakeEmbedder, build_embedder


def test_fake_embedder_is_deterministic_and_unit_norm():
    e = FakeEmbedder(dim=16)
    a = e.embed(["leash rules for dogs"])[0]
    b = e.embed(["leash rules for dogs"])[0]
    assert a.shape == (16,)
    assert np.allclose(a, b)
    assert abs(np.linalg.norm(a) - 1.0) < 1e-6


def test_fake_embedder_similar_texts_share_tokens():
    e = FakeEmbedder(dim=64)
    dog1, dog2, waste = e.embed(["dog leash trail", "dog leash park", "waste collection calendar"])
    assert float(dog1 @ dog2) > float(dog1 @ waste)


def test_build_embedder_fake():
    e = build_embedder("fake", model_name="ignored", dim=8)
    assert e.dim == 8
