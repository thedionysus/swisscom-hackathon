import urllib.request, json, re, ssl, sys
UA={'User-Agent':'Mozilla/5.0 swiss-grounding-check','Accept':'application/json, text/html;q=0.9, */*;q=0.8'}
def get(u, n=3_000_000):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40)
        return r.status, r.headers.get('Content-Type',''), r.geturl(), r.read(n)
    except urllib.error.HTTPError as e: return e.code,'',u,b''
    except Exception as e: return 0,str(e)[:80],u,b''
def show(label, *vals): print(f'[{label}]', *vals)

# 1 GR justice portal + sitemap
s,ct,f,b=get('https://www.justiz-gr.ch/sitemap.xml'); show('1 justiz-gr sitemap', s, len(re.findall(rb'<loc>',b)), 'locs')
# 2 GR 2025 merger quote
s,ct,f,b=get('https://www.justiz-gr.ch/gerichte/obergericht/ueber-uns/aufgaben/'); t=b.decode('utf-8','ignore')
m=re.search(r'[^.<>]{0,80}Zusammenf[^.<>]{0,120}',t); show('2 GR merger', s, m.group(0).strip() if m else 'NOT FOUND')
# 3 Lugano legislazione count + dog ordinance
s,ct,f,b=get('https://www.lugano.ch/la-mia-citta/amministrazione/legislazione.html'); t=b.decode('utf-8','ignore')
laws=sorted(set(re.findall(r'/law/(\d+)/',t))); show('3 Lugano', s, len(laws),'distinct /law/ ids; dog ordinance link present:', '16176713' in t)
s,ct,f,b=get('https://www.lugano.ch/law/16176713/2-6-1-Ordinanza-sulla-custodia-dei-cani-e-sulle-aree-di-svago-del-13-gennaio-2010')
open(sys.argv[1]+'/lugano_cani.pdf','wb').write(b); show('3b Lugano dog PDF', s, ct, len(b),'bytes', b[:5])
# 4 Amtsblattportal cantons= vs tenants=
base='https://amtsblattportal.ch/api/v1/publications?pageRequest.page=0&pageRequest.size=1&publicationDate.start=2026-09-01'
for q in ['', '&cantons=TI', '&cantons=VS', '&cantons=GR', '&tenants=kabti']:
    s,ct,f,b=get(base+q)
    try: d=json.loads(b); tot=d.get('total', d.get('totalElements', d.get('pageRequest'))) ; keys=list(d)[:6]
    except Exception: tot,keys='?',b[:120]
    show('4 amtsblatt'+(q or ' (no filter)'), s, 'total=',tot, keys)
# 5 VS JustSearch API
s,ct,f,b=get('https://api-justsearche.vs.ch/api/search/?offset=0&limit=2&sort=_score')
try: d=json.loads(b); show('5 VS api', s, 'count=', d.get('count'), 'keys', list(d)[:5])
except Exception: show('5 VS api', s, ct, b[:150])
# 6 TI root
s,ct,f,b=get('https://www4.ti.ch/'); show('6 TI root', s, '->', f)
# 7 entscheidsuche NeueScraper licence/pushed
s,ct,f,b=get('https://api.github.com/repos/entscheidsuche/NeueScraper')
try: d=json.loads(b); show('7 NeueScraper', s, (d.get('license') or {}).get('spdx_id'), 'pushed', d.get('pushed_at'))
except Exception: show('7 NeueScraper', s, b[:150])
# 8 opencaselaw atom freshness (one feed)
s,ct,f,b=get('https://mcp.opencaselaw.ch/api/atom/gr_gerichte.xml'); t=b.decode('utf-8','ignore')
show('8 atom gr', s, ct, 'entries', t.count('<entry'), 'feed updated', (re.search(r'<updated>([^<]+)',t) or [None,None])[1])
