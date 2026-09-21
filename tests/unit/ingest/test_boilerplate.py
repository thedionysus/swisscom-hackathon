from swiss_grounding.ingest.boilerplate import is_boilerplate


def test_navigation_heading_is_boilerplate():
    assert is_boilerplate(heading_path="Navigation", text_en="Read page aloud  Environment and Energy")


def test_error_page_title_is_boilerplate():
    assert is_boilerplate(heading_path="Error Page (404)", text_en="The page could not be found")


def test_real_article_is_not_boilerplate():
    assert not is_boilerplate(
        heading_path="Art. 28 Übrige Widerhandlungen",
        text_en="Anyone who intentionally, provided Article 26 is not applicable, is punished",
    )


def test_real_page_section_is_not_boilerplate():
    assert not is_boilerplate(
        heading_path="Der Wegweiser erklärt",
        text_en="Yellow signposts mark hiking trails and give walking times to the next destination.",
    )
