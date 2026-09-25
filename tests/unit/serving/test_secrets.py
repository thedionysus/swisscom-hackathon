from swiss_grounding.serving.secrets import HEADER, merge_env, parse_env, shared_env_text

KEY = "SUPERTEXT_API_KEY"
TOKEN = "ZBERN_MCP_TOKEN"


def test_parse_env_takes_only_the_shared_keys():
    text = "# comment\nSUPERTEXT_API_KEY = 'abc'\nOPENAI_API_KEY=nope\n\nDATABASE_URL=x\n"
    assert parse_env(text) == {KEY: "abc"}


def test_parse_env_ignores_a_commented_or_empty_shared_key():
    assert parse_env("# SUPERTEXT_API_KEY=\nSUPERTEXT_API_KEY=\n") == {}


def test_shared_env_text_is_one_line_per_key():
    assert shared_env_text({KEY: "abc", "OTHER": "x"}) == "SUPERTEXT_API_KEY=abc\n"
    assert shared_env_text({}) == ""


def test_merge_replaces_the_commented_example_line_in_place():
    env = "DATABASE_URL=x\n# SUPERTEXT_API_KEY=\n# TRANSLATE_CITATIONS=true\n"
    merged = merge_env(env, {KEY: "abc"})
    assert merged == "DATABASE_URL=x\nSUPERTEXT_API_KEY=abc\n# TRANSLATE_CITATIONS=true\n"


def test_merge_replaces_a_live_line_and_keeps_everything_else():
    env = "A=1\nSUPERTEXT_API_KEY=old\nB=2\n"
    assert merge_env(env, {KEY: "new"}) == "A=1\nSUPERTEXT_API_KEY=new\nB=2\n"


def test_merge_appends_under_a_header_when_the_key_is_absent():
    merged = merge_env("A=1\n", {KEY: "abc"})
    assert merged == f"A=1\n\n{HEADER}\nSUPERTEXT_API_KEY=abc\n"


def test_merge_into_an_empty_file():
    assert merge_env("", {KEY: "abc"}) == f"{HEADER}\nSUPERTEXT_API_KEY=abc\n"


def test_both_shared_keys_travel_together():
    text = shared_env_text({KEY: "abc", TOKEN: "tok"})
    assert text == "SUPERTEXT_API_KEY=abc\nZBERN_MCP_TOKEN=tok\n"
    assert parse_env(text) == {KEY: "abc", TOKEN: "tok"}
    merged = merge_env("A=1\n# ZBERN_MCP_TOKEN=\n", {KEY: "abc", TOKEN: "tok"})
    assert merged == f"A=1\nZBERN_MCP_TOKEN=tok\n\n{HEADER}\nSUPERTEXT_API_KEY=abc\n"


def test_merge_ignores_keys_that_are_not_shared_and_empty_values():
    env = "A=1\n"
    assert merge_env(env, {"OPENAI_API_KEY": "x", KEY: ""}) == env
