"""Compare the NEW parser's title/sections per saved page, default root vs a content_selector (offline)."""
import json, re, sys
from swiss_grounding.corpus.models import SourceSpec
from swiss_grounding.corpus.connectors.html_page import parse_crawled_page
S = "<scratchpad>"
idx = json.load(open(S + "/newpipe/saved_index.json"))
CASES = [  # (host regex, selector or None, language)
    (r"^https://www\.nw\.ch/(kantonsgericht|schlichtungsbeh|amtjustizdienste)", None, "de"),
    (r"^https://www\.ur\.ch/(rechtsgebiete|_rte/dienst/39)", None, "de"),
    (r"^https://www\.ow\.ch/(dienstleistungen|gerichte)", None, "de"),
    (r"^https://ar\.ch/(gerichte|verwaltung/departement-gesundheit|verwaltung/departement-inneres)", None, "de"),
    (r"^https://ar\.ch/(gerichte|verwaltung/departement-gesundheit|verwaltung/departement-inneres)", "#mainCol", "de"),
    (r"^https://www\.ai\.ch/(gerichte|themen/landwirtschaft|themen/mobilitaet|themen/bildung)", None, "de"),
    (r"^https://www\.ai\.ch/(gerichte|themen/landwirtschaft|themen/mobilitaet|themen/bildung)", "#content", "de"),
    (r"^https://www\.sg\.ch/(recht/gerichte|umwelt-natur|bildung-sport|verkehr)", None, "de"),
    (r"^https://www\.sg\.ch/(recht/gerichte|umwelt-natur|bildung-sport|verkehr)", "#maincontent", "de"),
    (r"^https://www\.gr\.ch/DE/institutionen/verwaltung/(dvs|djsg)", None, "de"),
    (r"^https://www\.gr\.ch/DE/institutionen/verwaltung/(dvs|djsg)", "div.pageContent", "de"),
    (r"^https://www\.ne\.ch/(themes|autorites)", None, "fr"),
    (r"^https://www\.jura\.ch/fr/Autorites/(JUST|Administration/(DES|DEC|DFNS))", None, "fr"),
    (r"^https://www\.justiz-gr\.ch/", None, "de"),
    (r"^https://www\.vs\.ch/web/", None, "fr"),
]
for host_re, sel, lang in CASES:
    cfg = {"start_urls": ["x"], "allow_prefixes": ["x"]}
    if sel:
        cfg["content_selector"] = sel
    spec = SourceSpec(id="t", name="t", publisher="t", authority="official_info", level="cantonal", extent_id="CH",
                      connector="html", tier=2, languages=(lang,), config=cfg)
    rows = []
    for url, path in sorted(idx.items()):
        if not re.search(host_re, url):
            continue
        raw = open(path, "rb").read()
        if b"<html" not in raw[:5000].lower():
            continue
        page = parse_crawled_page(raw.decode("utf-8", errors="replace"), url, spec, ())
        rows.append((url, page.title[:45], len(page.sections), sum(len(s.text) for s in page.sections)))
    print(f"### {host_re}  selector={sel}  pages={len(rows)}")
    for u, t, n, c in rows[:8]:
        print(f"    {t!r:50} sections={n:3} chars={c:6}  {u[:95]}")
