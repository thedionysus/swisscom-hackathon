#!/usr/bin/env python3
"""i-web content extractor: prints title, the text of wysiwyg/content blocks, and /_doc/ + external links.
Usage: iwc.py [-c CHARS] [-L N] URL..."""
import sys, os, re, html, argparse, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import fetch, analyse

ap = argparse.ArgumentParser()
ap.add_argument("-c", type=int, default=700)
ap.add_argument("-L", type=int, default=12)
ap.add_argument("urls", nargs="+")
a = ap.parse_args()

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

for u in a.urls:
    code, ct, size, final, body, fn = fetch(u)
    title, links, words, txt, raw = analyse(body)
    blocks = re.findall(r'<div class="icms-wysiwyg[^"]*">(.*?)</div>', raw, re.S)
    blocks += re.findall(r'<p class="icmsPContent[^"]*">(.*?)</p>', raw, re.S)
    heads = [clean(h) for h in re.findall(r'<h[12][^>]*class="icmsH[12]Content[^"]*"[^>]*>(.*?)</h[12]>', raw, re.S)]
    content = []
    for b in blocks:
        c = clean(b)
        if c and c not in content:
            content.append(c)
    body_txt = " / ".join(content)
    print(f"== {u} -> {code} {size}B final={final}\n   title='{title}' words={words} content_words={len(body_txt.split())}")
    if heads:
        print("   headings: " + " | ".join(heads[:10]))
    print("   content: " + body_txt[:a.c])
    raw2 = html.unescape(raw).replace("\\/", "/").replace('\\"', '"')
    docs = []
    for m in re.finditer(r'<a\s[^>]*href="([^"]*(?:_doc|_docn|\.pdf|http)[^"]*)"[^>]*>(.*?)</a>', raw2, re.S):
        h, t = m.group(1), clean(m.group(2))
        if re.search(r"facebook|linkedin|instagram|youtube|twitter|i-web\.ch|mailto", h):
            continue
        if (h, t) not in docs and ("_doc" in h or ".pdf" in h or not h.startswith(("https://www.ow.ch", "https://www.nw.ch", "https://www.ur.ch"))):
            docs.append((h, t))
    print(f"   doc/external links: {len(docs)}")
    for h, t in docs[:a.L]:
        print(f"    -> {h} [{t[:80]}]")
