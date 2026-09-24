import pytest

from swiss_grounding.corpus.describe import parse_chunk_reply, parse_doc_reply


def test_doc_reply_needs_every_language():
    ok = parse_doc_reply({"descriptions": {"de": "Das OR.", "fr": "Le CO."}, "topics": ["work", "nonsense"]},
                         languages=("de", "fr"))
    assert ok == ({"de": "Das OR.", "fr": "Le CO."}, ["work"])
    with pytest.raises(ValueError, match="fr"):
        parse_doc_reply({"descriptions": {"de": "Das OR."}, "topics": []}, languages=("de", "fr"))


def test_doc_reply_without_descriptions_object_is_rejected():
    with pytest.raises(ValueError, match="descriptions"):
        parse_doc_reply({"descriptions": ["Das OR."], "topics": []}, languages=("de",))


def test_chunk_reply_falls_back_to_prior_topics_and_caps_three():
    _, topics, boilerplate = parse_chunk_reply(
        {"descriptions": {"de": "x"}, "topics": [], "boilerplate": False}, languages=("de",), prior=["work"])
    assert topics == ["work"] and boilerplate is False
    _, topics, _ = parse_chunk_reply(
        {"descriptions": {"de": "x"}, "topics": ["work", "health", "taxes", "family"], "boilerplate": False},
        languages=("de",), prior=[])
    assert topics == ["work", "health", "taxes"]


def test_chunk_reply_ignores_non_list_topics_and_duplicates():
    _, topics, _ = parse_chunk_reply({"descriptions": {"de": "x"}, "topics": "work"}, ("de",), ["health"])
    assert topics == ["health"]
    _, topics, _ = parse_chunk_reply({"descriptions": {"de": "x"}, "topics": ["work", "work", 3]}, ("de",), [])
    assert topics == ["work"]


def test_chunk_reply_rejects_non_boolean_boilerplate():
    with pytest.raises(ValueError, match="boilerplate"):
        parse_chunk_reply({"descriptions": {"de": "x"}, "topics": [], "boilerplate": "no"}, ("de",), [])


def test_long_descriptions_are_trimmed():
    [(_, text)] = parse_doc_reply({"descriptions": {"de": "a" * 2000}, "topics": []}, ("de",))[0].items()
    assert len(text) == 600


def test_estimate_counts_languages_from_the_custom_id():
    from swiss_grounding.corpus.budget import cost_usd
    from swiss_grounding.corpus.describe import ESTIMATE_TOKENS_PER_LANGUAGE, estimate_describe
    from swiss_grounding.corpus.runner import LlmTask

    one = LlmTask(custom_id="doc|g_1|de", model="gpt-5-mini", system="s", user="u")
    three = LlmTask(custom_id="chunk|g_1|current|de=1,fr=2,it=3|art_1|x", model="gpt-5-mini", system="s", user="u")
    difference = estimate_describe([three], "gpt-5-mini") - estimate_describe([one], "gpt-5-mini")
    assert difference == pytest.approx(cost_usd("gpt-5-mini", 0, 2 * ESTIMATE_TOKENS_PER_LANGUAGE))


def test_nul_bytes_are_stripped_from_descriptions():
    """PostgreSQL rejects NUL (0x00) in text and jsonb; a model reply can carry one."""
    descriptions, _ = parse_doc_reply({"descriptions": {"de": "Das\x00 OR."}, "topics": []}, languages=("de",))
    assert descriptions == {"de": "Das OR."}
