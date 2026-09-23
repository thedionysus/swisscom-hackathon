#!/usr/bin/env python3
"""Probe URLs with curl; print status, content type, size, final URL, title, #links, words, grep snippets.
Usage: probe.py [-g REGEX] [-n N] [-w W] [-l LINKREGEX] [-a ACCEPT] [-m MARKER] [-c CHARS] URL...
Throttles www.sz.ch and www.gl.ch (>=5 s between requests, one retry after 20 s on 429)."""
import sys, subprocess, re, html, time, os, json, hashlib, argparse

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36 swiss-grounding-check")
D = "<scratchpad>/run3-b"
os.makedirs(D + "/pages", exist_ok=True)
SLOW = {"www.sz.ch": 5.0, "sz.ch": 5.0, "www.gl.ch": 5.0, "gl.ch": 5.0}
STATE = D + "/throttle.json"


def throttle(host):
    if host not in SLOW:
        return
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}
    last = st.get(host, 0)
    wait = SLOW[host] - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    st[host] = time.time()
    json.dump(st, open(STATE, "w"))


def fetch(url, accept=None, head=False):
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    fn = D + "/pages/" + hashlib.md5(url.encode()).hexdigest()[:12]
    for attempt in range(2):
        throttle(host)
        cmd = ["curl", "-sL", "-g", "--compressed", "--max-time", "60", "-A", UA, "-o", fn,
               "-w", "%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}"]
        if accept:
            cmd += ["-H", "Accept: " + accept]
        r = subprocess.run(cmd + [url], capture_output=True, text=True)
        code, ct, size, final = (r.stdout.split("\t") + ["", "", "", ""])[:4]
        if code == "429" and host in SLOW and attempt == 0:
            print(f"   (429 from {host}; waiting 20 s and retrying once)")
            time.sleep(20)
            continue
        break
    body = b""
    try:
        body = open(fn, "rb").read()
    except Exception:
        pass
    return code, ct, size, final, body, fn


def to_text(t):
    txt = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", t, flags=re.S | re.I)
    txt = html.unescape(re.sub(r"<[^>]+>", " ", txt))
    return re.sub(r"\s+", " ", txt)


def analyse(body):
    t = body.decode("utf-8", errors="ignore")
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    title = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""
    links = len(re.findall(r"<a\s[^>]*href", t, re.I))
    txt = to_text(t)
    return title, links, len(txt.split()), txt, t


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-g", "--grep")
    ap.add_argument("-n", type=int, default=3)
    ap.add_argument("-w", type=int, default=110, help="snippet half-width")
    ap.add_argument("-l", "--links", help="regex: print matching hrefs (with anchor text)")
    ap.add_argument("-L", type=int, default=60, help="max links printed")
    ap.add_argument("-a", "--accept")
    ap.add_argument("-m", "--marker", help="print text starting at this marker")
    ap.add_argument("-c", type=int, default=800, help="chars printed after marker")
    ap.add_argument("urls", nargs="+")
    a = ap.parse_args()
    for u in a.urls:
        code, ct, size, final, body, fn = fetch(u, a.accept)
        title, links, words, txt, raw = analyse(body)
        print(f"== {u}\n   {code} | {ct} | {size}B | final={final} | title='{title[:100]}' | links={links} | words={words} | file={fn}")
        if a.grep:
            n = 0
            for m in re.finditer(a.grep, txt, re.I):
                s = max(0, m.start() - a.w)
                print("   ~ " + txt[s:m.end() + a.w])
                n += 1
                if n >= a.n:
                    break
            if n == 0:
                print("   ~ (no match for grep)")
        if a.marker:
            i = txt.find(a.marker)
            print("   >> " + (txt[i:i + a.c] if i >= 0 else f"(marker '{a.marker}' not found)"))
        if a.links:
            seen = []
            for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', raw, re.I | re.S):
                h, anchor = m.group(1), re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
                if re.search(a.links, h + " " + anchor, re.I) and (h, anchor) not in seen:
                    seen.append((h, anchor))
            print(f"   links matching /{a.links}/: {len(seen)}")
            for h, anchor in seen[:a.L]:
                print(f"    -> {h}  [{anchor[:70]}]")
