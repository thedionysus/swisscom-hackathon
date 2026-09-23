from datetime import date

from swiss_grounding.corpus.connectors.html_meta import page_meta, work_key

HTML = """<html lang="de"><head>
<link rel="canonical" href="https://www.ch.ch/de/hund/">
<link rel="alternate" hreflang="de" href="https://www.ch.ch/de/hund/">
<link rel="alternate" hreflang="fr-CH" href="/fr/chien/">
<link rel="alternate" hreflang="x-default" href="/">
<meta property="article:modified_time" content="2026-03-12T08:00:00+01:00">
</head><body><main><h1>Hund</h1><p>Stand: 01.02.2026</p>
<a href="/files/merkblatt.pdf">Merkblatt Hundehaltung</a><a href="https://other.org/x.pdf">x</a>
</main></body></html>"""


def test_alternates_are_absolute_and_skip_x_default():
    meta = page_meta(HTML, "https://www.ch.ch/de/hund/")
    assert meta.alternates == {"de": "https://www.ch.ch/de/hund/", "fr": "https://www.ch.ch/fr/chien/"}
    assert meta.canonical == "https://www.ch.ch/de/hund/"


def test_modified_date_from_meta():
    assert page_meta(HTML, "https://www.ch.ch/de/hund/").modified == date(2026, 3, 12)


def test_modified_date_from_stand_text_when_no_meta():
    html = HTML.replace('<meta property="article:modified_time" content="2026-03-12T08:00:00+01:00">', "")
    assert page_meta(html, "https://www.ch.ch/de/hund/").modified == date(2026, 2, 1)


def test_pdf_links_with_text():
    links = page_meta(HTML, "https://www.ch.ch/de/hund/").pdf_links
    assert ("https://www.ch.ch/files/merkblatt.pdf", "Merkblatt Hundehaltung") in links


def test_work_key_is_shared_by_language_versions():
    de = work_key("https://www.ch.ch/de/hund/", {"de": "https://www.ch.ch/de/hund/", "fr": "https://www.ch.ch/fr/chien/"})
    fr = work_key("https://www.ch.ch/fr/chien/", {"de": "https://www.ch.ch/de/hund/", "fr": "https://www.ch.ch/fr/chien/"})
    assert de == fr
    assert work_key("https://x.ch/a", {}) == "html:https://x.ch/a"
