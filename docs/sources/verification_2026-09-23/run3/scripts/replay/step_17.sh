S=<scratchpad>
python3 - "$S" <<'E'
import json,sys,re,collections
from urllib.parse import urlparse
S=sys.argv[1];res=json.load(open(f'{S}/courts_s1_probe.json'))
NF=re.compile(r'404|not found|nicht gefunden|introuvable|non trovat|existiert nicht|n.existe pas|page not|fehler|erreur',re.I)
def norm(x): 
    p=urlparse(x);return (p.netloc.lower().removeprefix('www.'),p.path.rstrip('/'))
def cls(url,r):
    c=r.get('code')
    if c in ('ERR','000'): return 'no-response'
    if c!='200': return f'http-{c}'
    if NF.search(r.get('title','')): return 'soft-404'
    a,b=norm(url),norm(r['final'])
    if a==b: return 'ok'
    if b[1] in ('','/de','/fr','/it','/de/start.html') : return 'redirect-to-home'
    return 'redirect-elsewhere'
tab=collections.Counter();byg=collections.defaultdict(collections.Counter)
for url,r in res.items():
    k=cls(url,r);r['class']=k;tab[k]+=1;byg['direct' if r['grounded'] else 'wrapped'][k]+=1
json.dump(res,open(f'{S}/courts_s1_probe.json','w'),ensure_ascii=False,indent=1)
print('ALL',dict(tab));[print(g,dict(c),'of',sum(c.values())) for g,c in byg.items()]
print()
for k in ('ok','redirect-elsewhere','redirect-to-home','soft-404','no-response'):
    L=[(u,r) for u,r in res.items() if r['class']==k]
    print(f'== {k} ({len(L)})')
    for u,r in sorted(L)[:60]:
        extra='' if k in ('no-response',) else f"-> {r['final'][:90]} | {r['title'][:45]} | links {r['links']} words {r['words']}"
        print(('  [D] ' if r['grounded'] else '  [G] ')+u[:95],extra if k!='ok' else f"| {r['title'][:50]} | {r['size']}B links {r['links']} words {r['words']}")
codes=collections.Counter(r['code'] for r in res.values() if r['class'].startswith('http-'));print('\nhttp error codes',dict(codes))
E
