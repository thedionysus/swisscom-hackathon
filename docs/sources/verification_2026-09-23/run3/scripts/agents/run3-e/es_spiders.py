"""Download entscheidsuche NeueScraper spider files and the Spiderliste; extract per-spider base class, hosts, endpoints."""
import json, re, os, subprocess, urllib.parse
D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, 'es')
os.makedirs(OUT, exist_ok=True)
UA = 'Mozilla/5.0 swiss-grounding-check'
RAW = 'https://raw.githubusercontent.com/entscheidsuche/NeueScraper/master/'
tree = json.load(open(os.path.join(D, 'gh_tree.json')))['tree']
paths = [x['path'] for x in tree if x['path'].startswith('NeueScraper/spiders/') and x['path'].endswith('.py')]
paths += ['Description/Spiderliste.xlsx', 'Description/Description.xlsx', 's3 Anzeige/Spiderliste.xml', 'readme.txt']
for p in paths:
    fn = os.path.join(OUT, p.replace('/', '__'))
    if not os.path.exists(fn):
        subprocess.run(['curl', '-sL', '--max-time', '60', '-A', UA, '-o', fn, RAW + urllib.parse.quote(p)])
rows = []
for p in paths:
    if not p.endswith('.py'):
        continue
    fn = os.path.join(OUT, p.replace('/', '__'))
    t = open(fn, encoding='utf-8', errors='ignore').read()
    name = os.path.basename(p)[:-3]
    classes = re.findall(r'^class\s+(\w+)\s*\(([^)]*)\)', t, re.M)
    spider_name = re.findall(r'^\s*name\s*=\s*[\'"]([^\'"]+)', t, re.M)
    hosts = sorted(set(urllib.parse.urlparse(u).netloc for u in re.findall(r'https?://[^\s\'"\\)]+', t)))
    hosts = [h for h in hosts if h and 'entscheidsuche' not in h and 'w3.org' not in h and 'github' not in h]
    kinds = []
    for kw, lab in [('nph-omniscgi', 'Omnis FindinfoWeb CGI'), ('findinfo', 'FindInfo'), ('tribuna', 'Tribuna'), ('Tribuna', 'Tribuna'),
                    ('weblaw', 'Weblaw'), ('vaadin', 'Vaadin'), ('json', 'JSON'), ('/api/', 'API'), ('xml', 'XML'), ('rss', 'RSS'),
                    ('sitemap', 'sitemap'), ('.pdf', 'PDF'), ('FormRequest', 'POST form'), ('headless', 'headless browser'), ('selenium', 'selenium')]:
        if kw in t:
            kinds.append(lab)
    rows.append({'file': name, 'spider': spider_name[:1], 'classes': [f'{a}({b})' for a, b in classes][:2], 'hosts': hosts[:6], 'signals': sorted(set(kinds))})
json.dump(rows, open(os.path.join(D, 'es_spiders.json'), 'w'), ensure_ascii=False, indent=1)
for r in rows:
    print(r['file'], '|', r['spider'], '|', r['classes'], '|', r['hosts'], '|', r['signals'])
