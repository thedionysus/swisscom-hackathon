#!/usr/bin/env python3
"""Probe helper for run3-a.

Fetch each URL with curl (follow redirects, browser-like UA), then print
status | content-type | bytes | final URL | <title> | #<a href> | #words.

Options (apply to all URLs that follow them):
  -g REGEX   print up to N text snippets matching REGEX (after tag stripping)
  -n N       number of snippets for -g (default 4)
  -f REGEX   print hrefs matching REGEX (deduplicated, up to -m)
  -m N       max hrefs for -f (default 40)
  -a ACCEPT  send an Accept header
  -A UA      override the User-Agent
  -j         treat body as JSON: print top-level keys / length
  -q         quiet: only the status line

A per-host minimum delay is kept in .lastreq.json (BE/BS 10.5 s, SZ/GL 3.5 s).
Bodies are saved under pages/<slug>.
"""
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
from urllib.parse import urlparse, urljoin

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, ".lastreq.json")
PAGES = os.path.join(BASE, "pages")
os.makedirs(PAGES, exist_ok=True)
UA_DEFAULT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 swiss-grounding-check")
SLOW = {"be.ch": 10.5, "bs.ch": 10.5, "sz.ch": 3.5, "gl.ch": 3.5}


def delay_for(host):
    for suf, d in SLOW.items():
        if host == suf or host.endswith("." + suf):
            return d, suf
    return 0.5, host


def wait(host):
    d, key = delay_for(host)
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}
    last = st.get(key, 0)
    now = time.time()
    if now - last < d:
        time.sleep(d - (now - last))
    st[key] = time.time()
    json.dump(st, open(STATE, "w"))


def slug_for(url):
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    return re.sub(r"[^A-Za-z0-9]+", "_", url.split("//", 1)[-1])[:90] + "_" + h


def fetch(url, accept=None, ua=None):
    host = urlparse(url).hostname or ""
    wait(host)
    out = os.path.join(PAGES, slug_for(url))
    cmd = ["curl", "-g", "-sL", "--compressed", "-m", "45", "-A", ua or UA_DEFAULT, "-o", out,
           "-w", "%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}"]
    if accept:
        cmd += ["-H", "Accept: " + accept]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    parts = (r.stdout or "000\t\t0\t" + url).split("\t")
    while len(parts) < 4:
        parts.append("")
    return parts, out


def text_of(raw):
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    body = re.sub(r"(?s)<[^>]+>", " ", body)
    return html.unescape(re.sub(r"\s+", " ", body)).strip()


def main():
    args = sys.argv[1:]
    grep = None
    nsnip = 4
    hrefpat = None
    maxh = 40
    accept = None
    ua = None
    asjson = False
    quiet = False
    pdfhead = 0
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-g":
            grep = args[i + 1]; i += 2; continue
        if a == "-n":
            nsnip = int(args[i + 1]); i += 2; continue
        if a == "-f":
            hrefpat = args[i + 1]; i += 2; continue
        if a == "-m":
            maxh = int(args[i + 1]); i += 2; continue
        if a == "-a":
            accept = args[i + 1]; i += 2; continue
        if a == "-A":
            ua = args[i + 1]; i += 2; continue
        if a == "-j":
            asjson = True; i += 1; continue
        if a == "-q":
            quiet = True; i += 1; continue
        if a == "-p":
            pdfhead = int(args[i + 1]); i += 2; continue
        url = a
        i += 1
        (code, ctype, size, final), path = fetch(url, accept, ua)
        try:
            raw = open(path, "rb").read().decode("utf-8", "replace")
        except FileNotFoundError:
            raw = ""
        info = ""
        body = raw
        is_html = "html" in (ctype or "") or raw.lstrip()[:15].lower().startswith(("<!doctype", "<html"))
        if is_html:
            m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S | re.I)
            title = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip())[:100] if m else ""
            links = len(re.findall(r"<a\s[^>]*href", raw, re.I))
            body = text_of(raw)
            info = f" | title='{title}' | links={links} | words={len(body.split())}"
        if "pdf" in (ctype or "").lower() or raw[:5] == "%PDF-":
            try:
                import warnings
                warnings.filterwarnings("ignore")
                import logging
                logging.disable(logging.WARNING)
                from pypdf import PdfReader
                rd = PdfReader(path)
                ptxt = " ".join((rd.pages[k].extract_text() or "") for k in range(min(len(rd.pages), 3)))
                body = re.sub(r"\s+", " ", ptxt)
                info = f" | pdf_pages={len(rd.pages)} | text_chars_p1-3={len(body)}"
            except Exception as e:
                info = f" | pdf_error={str(e)[:60]}"
        print(f"{code} | {ctype} | {size}B | {final}{info} | file={os.path.basename(path)}")
        if quiet:
            continue
        if pdfhead and body is not raw:
            print("   pdf>", body[:pdfhead])
        if asjson:
            try:
                d = json.loads(raw)
                if isinstance(d, dict):
                    print("   json keys:", list(d.keys())[:25])
                elif isinstance(d, list):
                    print("   json list len:", len(d))
            except Exception as e:
                print("   json parse failed:", str(e)[:80], "| head:", raw[:200].replace("\n", " "))
        if grep:
            n = 0
            for mm in re.finditer(grep, body, re.I):
                s = body[max(0, mm.start() - 130): mm.end() + 170]
                print("   ~", s.replace("\n", " "))
                n += 1
                if n >= nsnip:
                    break
            if n == 0:
                print(f"   ~ (no match for {grep})")
        if hrefpat:
            seen = []
            for h in re.findall(r'href\s*=\s*["\']([^"\']+)["\']', raw, re.I):
                h = html.unescape(h)
                if re.search(hrefpat, h, re.I):
                    full = urljoin(final or url, h)
                    if full not in seen:
                        seen.append(full)
            print(f"   hrefs matching {hrefpat!r}: {len(seen)}")
            for h in seen[:maxh]:
                print("     ", h)


if __name__ == "__main__":
    main()
