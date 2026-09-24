from datetime import date
from pathlib import Path

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


# --- language alternates beyond hreflang -------------------------------------------------------

FIXTURES = Path(__file__).parents[2] / "fixtures" / "corpus"
CHCH_DE_URL = "https://www.ch.ch/de/gesundheit/krankenkasse/kosten-fur-krankenkasse/"
CHCH_FR_URL = "https://www.ch.ch/fr/assurances/assurance-maladie/couts-de-l-assurance-maladie/"


def _switcher(*links: str) -> str:
    return f"""<html lang="de"><body><nav id="language">{''.join(links)}</nav>
    <main><h1>T</h1><p>x</p></main></body></html>"""


def test_selector_links_give_alternates_from_their_text_code():
    meta = page_meta((FIXTURES / "chch_kk_de.html").read_text(), CHCH_DE_URL,
                     language_links_selector="nav#language a[href]")
    assert meta.alternates == {
        "de": CHCH_DE_URL,
        "fr": CHCH_FR_URL,
        "it": "https://www.ch.ch/it/assicurazioni/assicurazione-malattie/premi-delle-casse-malati/",
        "rm": "https://www.ch.ch/rm/assicuranzas/cassa-da-malsauns/custs-per-la-cassa-da-malsauns/",
        "en": "https://www.ch.ch/en/health/health-insurance/health-insurance-costs/",
    }


def test_selector_is_ignored_when_not_given():
    assert page_meta((FIXTURES / "chch_kk_de.html").read_text(), CHCH_DE_URL).alternates == {}


def test_selector_link_language_prefers_hreflang_and_lang_attributes():
    html = _switcher('<a href="/a" hreflang="fr-CH">Deutsch</a>', '<a href="/b" lang="it">EN</a>')
    meta = page_meta(html, "https://x.ch/de/", language_links_selector="nav#language a[href]")
    assert meta.alternates == {"fr": "https://x.ch/a", "it": "https://x.ch/b"}


def test_selector_link_language_from_language_name_then_url_segment():
    html = _switcher('<a href="/p/1">Français</a>', '<a href="/p/2"> Rumantsch </a>',
                     '<a href="/en/about">Switch</a>', '<a href="/p/3">Home</a>')
    meta = page_meta(html, "https://x.ch/de/", language_links_selector="nav#language a[href]")
    assert meta.alternates == {"fr": "https://x.ch/p/1", "rm": "https://x.ch/p/2", "en": "https://x.ch/en/about"}


def test_selector_links_outside_known_languages_are_dropped():
    html = _switcher('<a href="/es/">ES</a>', '<a href="/ja/">日本語</a>', '<a href="/fr/">FR</a>')
    meta = page_meta(html, "https://x.ch/de/", language_links_selector="nav#language a[href]")
    assert meta.alternates == {"fr": "https://x.ch/fr/"}


def test_hreflang_wins_over_selector_links():
    html = """<html><head><link rel="alternate" hreflang="fr" href="https://x.ch/fr/real"></head>
      <body><nav id="language"><a href="/fr/switcher">FR</a><a href="/it/switcher">IT</a></nav></body></html>"""
    meta = page_meta(html, "https://x.ch/de/", language_links_selector="nav#language a[href]")
    assert meta.alternates == {"fr": "https://x.ch/fr/real", "it": "https://x.ch/it/switcher"}


def test_nuxt_translation_pages_give_same_host_alternates():
    meta = page_meta((FIXTURES / "bag_kv_de.html").read_text(), "https://www.bag.admin.ch/de/krankenversicherung")
    assert meta.alternates == {
        "de": "https://www.bag.admin.ch/de/krankenversicherung",
        "fr": "https://www.bag.admin.ch/fr/assurance-maladie",
        "it": "https://www.bag.admin.ch/it/assicurazione-malattie",
        "en": "https://www.bag.admin.ch/en/health-insurance",
    }


def test_nuxt_payload_without_group_record_or_malformed_is_ignored():
    no_group = ('<html><body><script id="__NUXT_DATA__" type="application/json">'
                '[{"translationPages":1},[2],{"lang":3,"slug":4},"fr","x"]</script></body></html>')
    broken = '<html><body><script id="__NUXT_DATA__">[{"groupId": 1, "translationPages": 99}</script></body></html>'
    dangling = ('<html><body><script id="__NUXT_DATA__">'
                '[{"groupId":1,"translationPages":2},"g",[3, 42],{"lang":4,"slug":5},"fr","ok"]</script></body></html>')
    assert page_meta(no_group, "https://x.ch/de/a").alternates == {}
    assert page_meta(broken, "https://x.ch/de/a").alternates == {}
    assert page_meta(dangling, "https://x.ch/de/a").alternates == {"fr": "https://x.ch/fr/ok"}


def test_pdf_link_patterns_count_extensionless_links_as_pdfs():
    html = (FIXTURES / "ahv_merkblaetter_de.html").read_text()
    url = "https://www.ahv-iv.ch/de/Merkbl%C3%A4tter/Beitr%C3%A4ge-AHV/IV/EO/ALV"
    assert page_meta(html, url).pdf_links == ()
    links = page_meta(html, url, pdf_link_patterns=(r"^https://www\.ahv-iv\.ch/p/",)).pdf_links
    urls = [u for u, _ in links]
    assert "https://www.ahv-iv.ch/p/2.01.d" in urls
    assert all(u.startswith("https://www.ahv-iv.ch/p/") for u in urls)
    assert dict(links)["https://www.ahv-iv.ch/p/2.01.d"].startswith("2.01 - Lohnbeiträge")


def test_nuxt_self_referencing_wrappers_do_not_recurse_forever():
    looping = ('<html><body><script id="__NUXT_DATA__">'
               '[{"groupId":1,"lang":2,"translationPages":3},"g",["Reactive",2],["ShallowRef",4],'
               '["Reactive",3]]</script></body></html>')
    assert page_meta(looping, "https://x.ch/de/a").alternates == {}


def test_switcher_text_counts_only_when_it_is_wholly_a_language():
    html = _switcher('<a href="/fr/doc">Lire en ligne</a>', '<a href="/p/9">Italiano</a>')
    meta = page_meta(html, "https://x.ch/de/", language_links_selector="nav#language a[href]")
    assert meta.alternates == {"fr": "https://x.ch/fr/doc", "it": "https://x.ch/p/9"}
