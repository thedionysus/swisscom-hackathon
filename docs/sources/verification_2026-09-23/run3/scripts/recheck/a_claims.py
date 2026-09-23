import json, subprocess, re, sys, io, zipfile
S=sys.argv[1]; UA='Mozilla/5.0 swiss-grounding-check'
def get(u, acc='*/*', raw=False):
    r=subprocess.run(['curl','-s','-g','-L','--compressed','--max-time','90','-A',UA,'-H','Accept: '+acc,'-w','\n%{http_code}',u],capture_output=True)
    b,c=r.stdout.rsplit(b'\n',1); c=c.decode()
    return c,(b if raw else b.decode('utf-8','ignore'))
# 1 BL: public site vs backend API
c,b=get('https://www.baselland.ch/politik-und-behorden/gerichte','text/html'); print('[1 www.baselland.ch]',c,'| cloudflare challenge:', 'Just a moment' in b)
c,b=get('https://bl-api.webcloud7.ch/politik-und-behorden/gerichte','application/json')
try: d=json.loads(b); print('[1 bl-api]',c,d.get('@type'),'|',d.get('title'),'| items',len(d.get('items',[])),'| modified',d.get('modified'))
except Exception: print('[1 bl-api]',c,b[:120])
c,b=get('https://bl-api.webcloud7.ch/robots.txt','text/plain'); print('[1 bl-api robots.txt]',c,repr(b[:60]))
# 2 eSHAB export: XML with rubric BA-SO, and the same query as JSON
q='publicationStates=PUBLISHED&rubrics=BA-SO&publicationDate.start=2026-09-01&publicationDate.end=2026-09-23&pageRequest.page=0&pageRequest.size=2'
c,b=get('https://amtsblattportal.ch/api/v1/publications/xml?'+q,'application/xml'); m=re.search(r'<total>(\d+)</total>',b); print('[2 xml export]',c,'total',m.group(1) if m else b[:100])
c,b=get('https://amtsblattportal.ch/api/v1/publications?'+q,'application/json')
try: print('[2 same query as JSON]',c,'total',json.loads(b).get('total'))
except Exception: print('[2 same query as JSON]',c,b[:100])
# 3 robots of remaining gazette hosts
for h in ['amtsblatt.so.ch','kantonsblatt.ch','www.kantonsblatt.ch','amtsblatt.zh.ch','amtsblatt.be.ch','www.amtsblatt.bl.ch','amtsblatt.ag.ch']:
    c,b=get(f'https://{h}/robots.txt','text/plain'); dis=re.findall(r'(?im)^Disallow:\s*(\S*)',b)
    print(f'[3 robots {h}]',c,'full Disallow /:', '/' in dis, '| disallows:',dis[:4])
# 4 personal data in notices
c,b=get('https://amtsblattportal.ch/api/v1/publications?publicationStates=PUBLISHED&cantons=ZH&keyword=Todesanzeige&pageRequest.size=1&pageRequest.page=0','application/json')
try:
    d=json.loads(b); t=(d['content'][0]['meta'].get('title') or {}).get('de','') if d.get('content') else ''
    print('[4 ZH death notices]',c,'total',d.get('total'),'| first title starts:',t[:14])
except Exception: print('[4]',c,b[:100])
# 5 Bern SSSB PDF export for the dog regulation
c,b=get('https://stadtrecht.bern.ch/lex-559_61.pdf','application/pdf',raw=True); print('[5 Bern lex-559_61.pdf]',c,len(b),'bytes | is PDF:',b[:5]==b'%PDF-')
# 6 Thun i-web table
c,b=get('https://www.thun.ch/reglementeverordnungen','text/html'); m=re.search(r'data-entities="([^"]+)"',b)
if m:
    import html as H; ent=json.loads(H.unescape(m.group(1))); rows=ent.get('data',ent) if isinstance(ent,dict) else ent; s=json.dumps(rows,ensure_ascii=False)
    print('[6 Thun]',c,'rows',len(rows),'| rows mentioning Hund:',sum('Hund' in json.dumps(r,ensure_ascii=False) for r in rows))
# 7 commune directories
def xlsx_rows(u):
    c,b=get(u,'*/*',raw=True); z=zipfile.ZipFile(io.BytesIO(b)); names=[n for n in z.namelist() if n.startswith('xl/worksheets/sheet')]
    x=z.read(sorted(names)[0]).decode('utf-8','ignore'); ss=z.read('xl/sharedStrings.xml').decode('utf-8','ignore') if 'xl/sharedStrings.xml' in z.namelist() else ''
    return c,len(re.findall(r'<row ',x)),ss
c,n,ss=xlsx_rows('https://www.ag.ch/media/kanton-aargau/dfr/dokumente/statistik/statistische-daten/eckdaten-kt-aargau/gemeinden/gemeindeverzeichnis-ag-adressen-telefon.xlsx')
print('[7 AG xlsx]',c,'rows',n,'| has BFSNR:', 'BFSNR' in ss,'| has Internet:','Internet' in ss,'| Stand 16. September 2026:', '16. September 2026' in ss)
c,n,ss=xlsx_rows('https://www.gemeinden.dij.be.ch/content/dam/gemeinden_dij/dokumente/de/daten/gemeindedaten/adressliste%20einwohner-%20und%20gemischte%20gemeinden-de.xlsx')
print('[7 BE xlsx]',c,'rows',n,'| has Homepage:', 'Homepage' in ss)
c,b=get('https://data.bl.ch/api/explore/v2.1/catalog/datasets/10510/records?limit=1','application/json')
try: d=json.loads(b); print('[7 BL 10510]',c,'total_count',d.get('total_count'),'| website field:', 'website' in (d.get('results') or [{}])[0])
except Exception: print('[7 BL]',c,b[:100])
# 8 AG decisions DB now
c,b=get('https://agve.weblaw.ch/','text/html'); print('[8 agve.weblaw.ch]',c,'| unavailable text:', 'Unavailable' in b)
# 9 law_hits entries A calls wrong
lh=json.load(open(S+'/stage0/law_hits.json'))
print('[9 law_hits SO court_fees]', [(x['nr'],x['title'][:60]) for x in lh.get('SO',{}).get('court_fees',[])])
print('[9 law_hits AG court_fees]', lh.get('AG',{}).get('court_fees'))
