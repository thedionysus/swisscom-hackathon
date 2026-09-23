#!/usr/bin/env python3
"""curl-based probe: prints code, content-type, bytes, final url, title, #links, words, optional sample.

Usage:
  python3 probe.py 'URL::regex' 'URL2::regex2' ...
  python3 probe.py -f listfile        (one 'URL::regex' per line)
  python3 probe.py -L 'URL::linkregex' (print links whose href+label match linkregex)
Saves body to run3-d/pages/<slug>.
"""
import hashlib
import html
import os
import re
import subprocess
import sys
import time

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 swiss-grounding-check")
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "pages")
os.makedirs(OUT, exist_ok=True)


def slug(u):
    s = re.sub(r"[^A-Za-z0-9]+", "_", u)[:110]
    return s + "_" + hashlib.md5(u.encode()).hexdigest()[:6]


def fetch(url, extra=None):
    fn = os.path.join(OUT, slug(url))
    cmd = ["curl", "-g", "-sL", "--max-time", "45", "-A", UA, "-o", fn, "-w",
           "%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}"]
    if extra:
        cmd += extra
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    meta = r.stdout.strip().split("\t")
    while len(meta) < 4:
        meta.append("")
    return fn, meta


def page_text(raw):
    t = raw.decode("utf-8", "replace")
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    title = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""
    links = len(re.findall(r"<a\s[^>]*href", t, re.I))
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    text = re.sub(r"\s+", " ", text)
    return title, links, text


def link_list(raw, pat=None):
    t = raw.decode("utf-8", "replace")
    out = []
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', t, re.S | re.I):
        h = html.unescape(m.group(1))
        lab = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip())
        if pat is None or re.search(pat, h + " " + lab, re.I):
            out.append((h, lab[:100]))
    return out


def probe(url, rx=None, ctx=170, maxhits=2, linkmode=False):
    fn, (code, ct, size, final) = fetch(url)
    title = ""
    links = words = 0
    text = ""
    try:
        raw = open(fn, "rb").read()
    except FileNotFoundError:
        raw = b""
    is_html = "html" in ct or b"<html" in raw[:500].lower() or raw[:100].lstrip().startswith(b"<!")
    if "pdf" in ct or raw[:5] == b"%PDF-":
        try:
            from pypdf import PdfReader
            rd = PdfReader(fn)
            pages = len(rd.pages)
            text = " ".join((rd.pages[i].extract_text() or "") for i in range(min(pages, 4)))
            text = re.sub(r"\s+", " ", text)
            title = f"[PDF {pages} pages, text chars p1-4: {len(text)}]"
            words = len(text.split())
        except Exception as e:  # noqa
            title = f"[PDF read error {e}]"
    elif is_html:
        title, links, text = page_text(raw)
        words = len(text.split())
    else:
        text = raw[:6000].decode("utf-8", "replace")
    print(f"==> {url}\n{code} | {ct} | {size}B | {final}\n   title: {title[:120]}\n"
          f"   links={links} words={words}  file={os.path.basename(fn)}")
    if rx and not linkmode:
        hits = 0
        for m in re.finditer(rx, text, re.I):
            s = max(0, m.start() - ctx // 2)
            print("   SAMPLE:", text[s:m.end() + ctx].strip()[:ctx * 2])
            hits += 1
            if hits >= maxhits:
                break
        if hits == 0:
            print("   SAMPLE: <no match for", rx, ">")
    if linkmode:
        for h, lab in link_list(raw, rx):
            print("   LINK:", h, "|", lab)
    sys.stdout.flush()


if __name__ == "__main__":
    args = sys.argv[1:]
    linkmode = False
    items = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-f":
            items += [ln.strip() for ln in open(args[i + 1]) if ln.strip() and not ln.startswith("#")]
            i += 2
            continue
        if a == "-L":
            linkmode = True
            i += 1
            continue
        items.append(a)
        i += 1
    for it in items:
        if "::" in it:
            u, rx = it.split("::", 1)
        else:
            u, rx = it, None
        probe(u, rx, linkmode=linkmode)
        time.sleep(0.4)
