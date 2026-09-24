"""Run the NEW pipeline's page parser on saved pages (offline). Usage: offline_parse.py <host-regex> [content_selector] [lang]"""
import json, re, sys
from bs4 import BeautifulSoup
from swiss_grounding.corpus.models import SourceSpec
from swiss_grounding.corpus.connectors.html_page import parse_crawled_page
from swiss_grounding.ingest.html_sections import html_to_page, _content_root, MAIN_CANDIDATES

S = "<scratchpad>"
idx = json.load(open(S + "/newpipe/saved_index.json"))
host_re = re.compile(sys.argv[1])
selector = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else None
lang = sys.argv[3] if len(sys.argv) > 3 else "de"
cfg = {"start_urls": ["x"], "allow_prefixes": ["x"]}
if selector:
    cfg["content_selector"] = selector
spec = SourceSpec(id="t", name="t", publisher="t", authority="official_info", level="cantonal", extent_id="CH",
                  connector="html", tier=2, languages=(lang,), config=cfg)
for url, path in sorted(idx.items()):
    if not host_re.search(url):
        continue
    raw = open(path, "rb").read()
    head = raw[:600].lower()
    if b"<html" not in raw[:5000].lower() and b"<!doctype html" not in head:
        continue
    html = raw.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    root = _content_root(soup, selector)
    root_desc = f"<{root.name} id={root.get('id')!r} class={' '.join(root.get('class') or [])[:40]!r}>" if root is not None else None
    forms = len(soup.find_all("form"))
    body_forms = [f for f in soup.find_all("form") if f.find_parent("body") is not None and len(f.get_text(" ", strip=True)) > 500]
    page = parse_crawled_page(html, url, spec, ())
    chars = sum(len(s.text) for s in page.sections)
    print(f"{url}\n   root={root_desc} forms={forms} big_forms={len(body_forms)} -> title={page.title[:60]!r} sections={len(page.sections)} chars={chars} lang={page.language} emit={page.emit} pdf_links={len(page.pdf_links)}")
