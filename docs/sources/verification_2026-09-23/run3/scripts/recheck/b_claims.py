import json, subprocess, re, collections, sys
S=sys.argv[1]; UA='Mozilla/5.0 swiss-grounding-check'
def get(u, acc='application/json'):
    r=subprocess.run(['curl','-s','-g','-L','--compressed','--max-time','60','-A',UA,'-H','Accept: '+acc,'-w','\n%{http_code}',u],capture_output=True,text=True)
    b,c=r.stdout.rsplit('\n',1); return c,b
# 1 robots.txt of gazette hosts (tenant domains and the central portal)
for h in ['amtsblatt.zg.ch','amtsblatt.sz.ch','amtsblattportal.ch','www.amtsblattportal.ch','foglioufficiale.ti.ch','bulletin-officiel.vs.ch']:
    c,b=get(f'https://{h}/robots.txt','text/plain'); print(f'[1 robots {h}]',c,repr(b.strip()[:80]))
# 2 ZG gazette count in ZG's own rubrics (codes from B's saved rubric list)
rub=json.load(open(f'{S}/run3-b/pages/zg_rubrics.json'))
codes=[r['code'] for r in rub if r.get('tenantId')=='kabzg']
base='https://amtsblatt.zg.ch/api/v1/publications?publicationStates=PUBLISHED&pageRequest.page=0&pageRequest.size=1'
for label,q in [('tenant+rubrics',f'&tenant=kabzg&rubrics={",".join(codes)}'),('tenant only','&tenant=kabzg'),('cantons=ZG','&cantons=ZG')]:
    c,b=get(base+q)
    try: tot=json.loads(b).get('total')
    except Exception: tot=b[:80]
    print(f'[2 ZG gazette {label}]',c,'total=',tot,'| rubric codes:',codes if label=='tenant+rubrics' else '')
# 3 ZG Steuerbuch Plone backend
c,b=get('https://wissen-backend.webcloud7.ch/steuerbuch'); d=json.loads(b)
print('[3 ZG Steuerbuch root]',c,d.get('@type'),'|',d.get('title'),'| modified',d.get('modified'))
c,b=get('https://wissen-backend.webcloud7.ch/steuerbuch/@search?b_size=1'); print('[3 @search]',c,'items_total=',json.loads(b).get('items_total'))
# 4 SZ holidays dataset
c,b=get('https://data.sz.ch/api/explore/v2.1/catalog/datasets/ferienplan-kanton-schwyz'); d=json.loads(b)
meta=d.get('metas',{}).get('default',{}); print('[4 SZ dataset]',c,'licence=',meta.get('license'),'| records=',meta.get('records_count'),'| modified=',meta.get('modified'))
c,b=get('https://data.sz.ch/api/explore/v2.1/catalog/datasets/ferienplan-kanton-schwyz/records?limit=1'); d=json.loads(b)
print('[4 SZ record fields]',c,'total_count=',d.get('total_count'),'| fields=',sorted((d.get('results') or [{}])[0].keys()))
# 5 NW cantonal dog tax
c,b=get('https://www.nw.ch/amtjustizdienste/581','text/html'); t=re.sub(r'<[^>]+>',' ',b)
m=re.search(r'Hundesteuer im Kanton[^.]{0,80}\.',t); print('[5 NW dog tax]',c, m.group(0) if m else 'NOT FOUND')
# 6 OW opencaselaw freshness (Stage 0 file, rebuilt today)
oc=json.load(open(f'{S}/opencaselaw_courts_2026-09-23.json'))
items=oc if isinstance(oc,list) else oc.get('courts',oc)
for it in items:
    s=json.dumps(it)
    if '"ow_' in s or '"zg_kantonsgericht"' in s: print('[6 opencaselaw]',s[:200])
