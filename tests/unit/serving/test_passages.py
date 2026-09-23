from swiss_grounding.serving.passages import MAX_PASSAGE_CHARS, best_passage


def test_short_text_is_returned_whole():
    assert best_passage("Drei Monate.", ["Frist"]) == "Drei Monate."


def test_picks_the_window_sharing_most_words_with_the_queries():
    text = " ".join([f"Satz {i} über etwas anderes." for i in range(40)]
                    + ["Die Kündigungsfrist beträgt drei Monate."]
                    + [f"Nachsatz {i} ohne Bezug." for i in range(40)])
    passage = best_passage(text, ["Wie lange ist die Kündigungsfrist?"])
    assert "Kündigungsfrist beträgt drei Monate" in passage
    assert len(passage) <= MAX_PASSAGE_CHARS


def test_numbers_count_as_words():
    text = "Absatz eins über Hunde. " * 30 + "Art. 336c gilt hier. " + "Absatz zwei über Katzen. " * 30
    assert "336c" in best_passage(text, ["336c"])
