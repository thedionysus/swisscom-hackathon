import json, subprocess, re, sys, io, zipfile, html as H
S=sys.argv[1]; UA='Mozilla/5.0 swiss-grounding-check'
def get(u, acc='*/*', raw=False):
    r=subprocess.run(['curl','-s','-g','-L','--compressed','--max-time','90','-A',UA,'-H','Accept: '+acc,'-w','\n%{http_code}',u],capture_output=True)
    b,c=r.stdout.rsplit(b'\n',1); c=c.decode(); return c,(b if raw else b.decode('utf-8','ignore'))
c,b=get('https://www.gemeinden.dij.be.ch/de/start/daten/gemeindedaten.html','text/html')
links=[H.unescape(x) for x in re.findall(r'href="([^"]+\.xlsx)"',b)]
target=[l for l in links if 'adressliste' in l.lower() and 'einwohner' in l.lower()]
print('[7 BE page]',c,'xlsx links',len(links),'| target:',target[:1])
if target:
    u=target[0] if target[0].startswith('http') else 'https://www.gemeinden.dij.be.ch'+target[0]
    c,raw=get(u.replace(' ','%20'),raw=True); z=zipfile.ZipFile(io.BytesIO(raw))
    x=z.read(sorted(n for n in z.namelist() if n.startswith('xl/worksheets/sheet'))[0]).decode('utf-8','ignore')
    ss=z.read('xl/sharedStrings.xml').decode('utf-8','ignore') if 'xl/sharedStrings.xml' in z.namelist() else ''
    print('[7 BE xlsx]',c,'rows',len(re.findall(r'<row ',x)),'| Homepage column:', 'Homepage' in ss)
c,b=get('https://data.bl.ch/api/explore/v2.1/catalog/datasets/10510/records?limit=1','application/json')
d=json.loads(b); print('[7 BL 10510]',c,'total_count',d.get('total_count'),'| website field:', 'website' in (d.get('results') or [{}])[0])
c,b=get('https://agve.weblaw.ch/','text/html'); print('[8 agve.weblaw.ch now]',c,'| "Unavailable" in body:', 'Unavailable' in b)
lh=json.load(open(S+'/stage0/law_hits.json'))
print('[9 law_hits SO court_fees]', [(x['nr'],x['title'][:70]) for x in lh.get('SO',{}).get('court_fees',[])])
print('[9 law_hits AG court_fees]', lh.get('AG',{}).get('court_fees'))
