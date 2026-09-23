"""python3 lexgrep.py HOST LANG NR REGEX [NR REGEX ...] : LexWork show_as_json + metadata, grep article text."""
import sys, json, re, html, subprocess
UA = 'Mozilla/5.0 swiss-grounding-check'
host, lang = sys.argv[1], sys.argv[2]
args = sys.argv[3:]
for i in range(0, len(args), 2):
    nr, rx = args[i], args[i + 1]
    meta = subprocess.run(['curl', '-sL', '--compressed', '--max-time', '60', '-A', UA, f'https://{host}/api/{lang}/texts_of_law/{nr}'], capture_output=True, text=True).stdout
    try:
        m = json.loads(meta)
        tl = m.get('text_of_law', m)
        print('==', nr, '|', tl.get('title'), '| enactment', tl.get('enactment'), '| canonical', tl.get('canonical_link'), '| abrogated', tl.get('abrogated'))
    except Exception as e:
        print('==', nr, 'meta parse error', meta[:120])
    r = subprocess.run(['curl', '-sL', '--compressed', '--max-time', '60', '-A', UA, '-w', '\n%{http_code}', f'https://{host}/api/{lang}/texts_of_law/{nr}/show_as_json'], capture_output=True, text=True).stdout
    body, code = r.rsplit('\n', 1)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', json.dumps(json.loads(body), ensure_ascii=False) if body.strip().startswith('{') else body))
    t = re.sub(r'\\[nrt]', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    print('   show_as_json', code, len(body), 'bytes')
    for mm in list(re.finditer(rx, t))[:3]:
        print('   ..', t[max(0, mm.start() - 160):mm.end() + 160])
