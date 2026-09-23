import sys, os, re, json, subprocess, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h
UA = 'Mozilla/5.0 swiss-grounding-check'

def get(u, accept=None):
    cmd = ['curl', '-sL', '--compressed', '--max-time', '60', '-A', UA, '-w', '\n%{http_code}|%{content_type}|%{size_download}']
    if accept:
        cmd += ['-H', 'Accept: ' + accept]
    r = subprocess.run(cmd + [u], capture_output=True)
    body, tail = r.stdout.rsplit(b'\n', 1)
    return body.decode('utf-8', errors='ignore'), tail.decode()

# 1. Onlinekommentar OAI sets
b, t = get('https://onlinekommentar.ch/oai?verb=ListSets')
print('OK ListSets', t, '| sets:', re.findall(r'<setSpec>([^<]+)</setSpec>', b)[:40])

# 2. CLDS databases list
L = h.links('p_18ea8ceee6')
print('\nCLDS links (external):')
seen = set()
for x, tx in L:
    if x.startswith('http') and 'uzh.ch' not in x and x not in seen and not re.search('facebook|twitter|linkedin|instagram|youtube|x.com', x):
        seen.add(x)
        print('  ', tx[:70], '|', x)

# 3. opencaselaw Atom feeds
for c in ['ti_gerichte', 'gr_gerichte', 'vs_gerichte']:
    u = f'https://mcp.opencaselaw.ch/api/atom/{c}.xml'
    b, t = get(u)
    entries = re.findall(r'<entry>(.*?)</entry>', b, re.S)
    upd = re.findall(r'<updated>([^<]+)</updated>', b)
    print(f'\n{c}: {t} | entries {len(entries)} | feed updated {upd[:1]}')
    print('   head:', re.sub(r'\s+', ' ', b[:300]))
    for e in entries[:2]:
        fields = {k: re.sub(r'\s+', ' ', html.unescape(v))[:110] for k, v in re.findall(r'<(title|updated|published|id|summary)[^>]*>(.*?)</\1>', e, re.S)}
        links = re.findall(r'<link[^>]*href="([^"]+)"', e)
        print('   entry:', fields, '| links', links[:2])
    dates = sorted(set(d[:10] for d in re.findall(r'<(?:updated|published)>([^<]+)<', ''.join(entries))))
    if dates:
        print('   entry date range:', dates[0], '->', dates[-1])
