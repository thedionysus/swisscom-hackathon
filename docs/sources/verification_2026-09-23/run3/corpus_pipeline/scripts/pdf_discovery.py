"""Which PDF links would the NEW html connector discover on a saved page? (offline)
usage: pdf_discovery.py <url> [pdf_link_pattern ...]"""
import json, re, sys
from swiss_grounding.corpus.connectors.html_meta import page_meta
from swiss_grounding.ingest.html_sections import extract_links
S = "<scratchpad>"
idx = json.load(open(S + "/newpipe/saved_index.json"))
url = sys.argv[1]
pats = sys.argv[2:]
if url not in idx:
    print("NOT SAVED:", url); sys.exit()
html = open(idx[url], "rb").read().decode("utf-8", errors="replace")
meta = page_meta(html, url, pdf_link_patterns=pats)
print(f"{url}: {len(meta.pdf_links)} PDF links (patterns={pats})")
for href, text in meta.pdf_links[:60]:
    print("   PDF", href, "|", text[:60])
links = extract_links(html, url)
print(f"   {len(links)} links total")
