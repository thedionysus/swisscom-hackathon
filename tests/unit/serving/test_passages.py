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


# ch.ch passport page as stored (1,560 characters): the child rules come first, the adult validity last.
PASSPORT_CHUNK = (
    '* You can only apply for an identity document for your child if you have parental authority.\n'
    '* If both parents have parental authority, the signature of one parent is usually enough to apply for an identity document. Contact your canton to find out if other rules apply.\n'
    '* However, if joint parental authority is difficult to prove (e.g. if the parents live at two different addresses), you will also have to provide the consent of the other parent.\n'
    '* Children aged seven and older are required to sign their identity document.\n'
    '* Children aged 12 and older are required to provide digital fingerprints for their biometric passport.\n'
    '* Once your children turn 18, they have to apply for their own identity documents.\n'
    '\n'
    'Biometric data and photographs\n'
    '\n'
    'Applicants for identity documents must provide biometric data (data stored on a microchip including a facial photograph and signature – and fingerprints for passports – which are protected from abuse) to the cantonal authorities or a Swiss representation abroad.\n'
    '\n'
    'The photograph is generally taken when the biometric data is recorded. However, some cantons allow you to use your own photograph. In such cases the photograph must meet specific requirements: contact your cantonal authority for full details.\n'
    '\n'
    'If you apply for an identity card from your commune\xa0, you must provide a facial photograph that complies with specific rules:\n'
    '\n'
    'Validity\n'
    '\n'
    'Passports and identity cards are valid for 10 years for adults and for 5 years for children and adolescents under the age of 18.\n'
    '\n'
    'Expired identity and travel documents'
)


def test_answer_late_in_a_chunk_is_not_cut_out():
    passage = best_passage(PASSPORT_CHUNK, ["How long is a Swiss passport valid for an adult?"])
    assert "valid for 10 years for adults" in passage


def test_table_keeps_its_header():
    text = ("Please note: a temporary passport is not biometric. " * 12
            + "\n\nPrices\n\n| | Identity Card | Passport |\n| --- | --- | --- |\n"
            + "| **Adults** | 65.- CHF | 140.- CHF |\n| **Children** | 30.- CHF | 60.- CHF |\n"
            + "\nIf you lose your identity card, see Lost or stolen passport or identity card.")
    passage = best_passage(text, ["What is the official fee for a Swiss identity card for an adult?"])
    assert "| Identity Card |" in passage and "| **Adults** | 65.- CHF" in passage
