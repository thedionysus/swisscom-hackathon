"""Scratch helper for run3-e. Usage:
  python3 h.py probe URL [URL ...]            status | type | bytes | links | words | title | final | file
  python3 h.py links FILE [regex]             list <a href> (filtered by regex on href or text)
  python3 h.py text FILE [N]                  main text, first N chars
  python3 h.py grep FILE kw1 [kw2 ...]        main-text snippets around each keyword (3 per kw)
Env: UA (user agent), ACCEPT (Accept header), SLEEP (seconds between probes).
"""
import sys, subprocess, re, html, hashlib, os, time

D = os.path.dirname(os.path.abspath(__file__))
UA = os.environ.get('UA', 'Mozilla/5.0 swiss-grounding-check')


def fname(url):
    return os.path.join(D, 'p_' + hashlib.md5(url.encode()).hexdigest()[:10])


def probe(url, quiet=False):
    fn = fname(url)
    cmd = ['curl', '-sL', '-g', '--compressed', '--max-time', '45', '-A', UA, '-o', fn,
           '-w', '%{http_code}|%{content_type}|%{size_download}|%{url_effective}']
    if os.environ.get('ACCEPT'):
        cmd += ['-H', 'Accept: ' + os.environ['ACCEPT']]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    code, ct, size, final = (r.stdout.split('|') + ['', '', '', ''])[:4]
    title = ''
    links = words = 0
    try:
        b = open(fn, 'rb').read()
        t = b.decode('utf-8', errors='ignore')
        if 'html' in ct or t.lstrip()[:15].lower().startswith(('<!doctype', '<html')):
            m = re.search(r'<title[^>]*>(.*?)</title>', t, re.S | re.I)
            title = html.unescape(re.sub(r'\s+', ' ', m.group(1))).strip()[:90] if m else ''
            links = len(re.findall(r'<a\s[^>]*href', t, re.I))
            body = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', t, flags=re.S | re.I)
            words = len(re.sub(r'<[^>]+>', ' ', body).split())
    except Exception:
        pass
    if not quiet:
        print(f'{code} | {ct[:28]} | {size}B | links {links} | words {words} | {title} | {final} | {os.path.basename(fn)}')
    return fn, code, ct, size, final, title


def read(fn):
    if not os.path.exists(fn):
        fn = os.path.join(D, fn)
    return open(fn, 'rb').read().decode('utf-8', errors='ignore')


def main_text(fn, markers=('id="maincontent"', 'id="main-content"', '<main', 'id="content"', 'role="main"')):
    t = read(fn)
    body = re.sub(r'<script.*?</script>|<style.*?</style>|<nav.*?</nav>|<header.*?</header>', ' ', t, flags=re.S | re.I)
    for m in markers:
        i = body.find(m)
        if i >= 0:
            body = body[i:]
            break
    txt = html.unescape(re.sub(r'<[^>]+>', ' ', body))
    return re.sub(r'\s+', ' ', txt)


def links(fn, filt=None):
    t = read(fn)
    out = []
    for h, txt in re.findall(r'<a\s[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', t, re.S | re.I):
        txt = html.unescape(re.sub(r'<[^>]+>|\s+', ' ', txt)).strip()
        if filt and not (re.search(filt, h, re.I) or re.search(filt, txt, re.I)):
            continue
        out.append((html.unescape(h), txt[:90]))
    return out


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'probe':
        s = float(os.environ.get('SLEEP', '0'))
        for i, u in enumerate(sys.argv[2:]):
            if i and s:
                time.sleep(s)
            probe(u)
    elif cmd == 'links':
        seen = set()
        for h, t in links(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None):
            if (h, t) in seen:
                continue
            seen.add((h, t))
            print(h, '|', t)
    elif cmd == 'text':
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
        print(main_text(sys.argv[2])[:n])
    elif cmd == 'grep':
        txt = main_text(sys.argv[2])
        for kw in sys.argv[3:]:
            for mm in list(re.finditer(kw, txt, re.I))[:3]:
                print(f'[{kw}]', txt[max(0, mm.start() - 180):mm.end() + 180])
                print()
