#!/usr/bin/env python3
"""Probe URLs: status, content type, size, final URL, <title>, #links, #words; optional samples.
usage: probe.py [-g REGEX] [-n N] [-m MARKER] [-l LINKREGEX] [-L N] [-d SECONDS] [-c] URL [URL ...]
  -g REGEX      print up to N text snippets matching REGEX (tags stripped)
  -m MARKER     take text only from the first occurrence of MARKER in the HTML onwards
  -l LINKREGEX  list <a href> whose href or anchor text matches LINKREGEX (max -L, default 40)
  -d SECONDS    sleep between requests
  -c            use a full desktop Chrome User-Agent
Every request is appended to requests.jsonl (url, code, ct, size, final, title).
"""
import sys, subprocess, re, os, html, hashlib, time, json

BASE = '<scratchpad>/run3-c'
UA = 'Mozilla/5.0 swiss-grounding-check'
CHROME = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
OUT = os.path.join(BASE, 'pages')
os.makedirs(OUT, exist_ok=True)


def slug(u):
    s = re.sub(r'[^A-Za-z0-9]+', '_', u.split('://', 1)[-1])[:90]
    return s + '_' + hashlib.md5(u.encode()).hexdigest()[:6]


def fetch(url, ua):
    fn = os.path.join(OUT, slug(url))
    r = subprocess.run(['curl', '-sL', '-g', '--compressed', '--max-time', '40', '-A', ua, '-o', fn,
                        '-w', '%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}', url],
                       capture_output=True, text=True)
    parts = (r.stdout or '000\t\t0\t' + url).split('\t')
    code, ct, size, final = (parts + ['', '', '', ''])[:4]
    body = b''
    if os.path.exists(fn):
        body = open(fn, 'rb').read()
    return code, ct, size, final, body, fn


def text_of(s):
    t = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', s)
    t = re.sub(r'(?s)<[^>]+>', ' ', t)
    t = html.unescape(t)
    return re.sub(r'\s+', ' ', t).strip()


def main():
    args = sys.argv[1:]
    pat = None
    n = 3
    marker = None
    linkpat = None
    lmax = 40
    delay = 0.0
    ua = UA
    while args and args[0].startswith('-'):
        a = args.pop(0)
        if a == '-g':
            pat = re.compile(args.pop(0), re.I)
        elif a == '-n':
            n = int(args.pop(0))
        elif a == '-m':
            marker = args.pop(0)
        elif a == '-l':
            linkpat = re.compile(args.pop(0), re.I)
        elif a == '-L':
            lmax = int(args.pop(0))
        elif a == '-d':
            delay = float(args.pop(0))
        elif a == '-c':
            ua = CHROME
    for i, u in enumerate(args):
        if i and delay:
            time.sleep(delay)
        code, ct, size, final, body, fn = fetch(u, ua)
        s = body.decode('utf-8', errors='ignore')
        m = re.search(r'(?is)<title[^>]*>(.*?)</title>', s)
        title = html.unescape(re.sub(r'\s+', ' ', m.group(1))).strip()[:100] if m else ''
        links = len(re.findall(r'(?i)<a\s[^>]*href', s))
        is_html = 'html' in ct or s.lstrip()[:1] == '<'
        txt = text_of(s) if is_html else ''
        words = len(txt.split())
        if marker and is_html:
            k2 = s.find(marker)
            if k2 >= 0:
                txt = text_of(s[k2:])
        print(f'{code} | {ct[:40]} | {size}B | links {links} | words {words} | title: {title}')
        print(f'   url: {u}')
        if final != u:
            print(f'   final: {final}')
        print(f'   file: {fn}')
        with open(os.path.join(BASE, 'requests.jsonl'), 'a') as fh:
            fh.write(json.dumps({'t': time.strftime('%H:%M:%S'), 'url': u, 'code': code, 'ct': ct, 'size': size,
                                 'final': final, 'title': title, 'links': links, 'words': words},
                                ensure_ascii=False) + '\n')
        if pat is not None and txt:
            k = 0
            for mm in pat.finditer(txt):
                a, b = max(0, mm.start() - 110), min(len(txt), mm.end() + 170)
                print('   >> ' + txt[a:b])
                k += 1
                if k >= n:
                    break
            if k == 0:
                print('   >> (no match)')
        if linkpat is not None and is_html:
            src = s
            if marker:
                k2 = s.find(marker)
                if k2 >= 0:
                    src = s[k2:]
            seen = set()
            k = 0
            for h, a in re.findall(r'(?is)<a\s[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', src):
                at = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', a))).strip()
                if (linkpat.search(h) or linkpat.search(at)) and h not in seen:
                    seen.add(h)
                    print(f'   -> {h[:170]} | {at[:80]}')
                    k += 1
                    if k >= lmax:
                        break
            print(f'   (links matched: {k}{"+" if k >= lmax else ""})')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
