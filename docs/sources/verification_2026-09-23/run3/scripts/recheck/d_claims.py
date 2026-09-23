import json, subprocess, re, sys, socket
S=sys.argv[1]; UA='Mozilla/5.0 swiss-grounding-check'
def get(u, acc='*/*', data=None, ctype=None, follow=True):
    cmd=['curl','-s','-g','--compressed','--max-time','90','-A',UA,'-H','Accept: '+acc,'-w','\n%{http_code} %{url_effective}']
    if follow: cmd.append('-L')
    if data is not None: cmd+=['-X','POST','-H','Content-Type: '+(ctype or 'application/json'),'--data',data]
    r=subprocess.run(cmd+[u],capture_output=True,text=True); b,meta=r.stdout.rsplit('\n',1); code,eff=meta.split(' ',1); return code,b,eff
# 1 NE sitemap: children on an internal host; same paths on www.ne.ch
c,b,_=get('https://www.ne.ch/sitemap.xml','application/xml'); kids=re.findall(r'<loc>([^<]+)</loc>',b)
print('[1 NE index]',c,kids)
try: socket.gethostbyname('ne-prod-admin.ne.ch'); print('   ne-prod-admin.ne.ch resolves')
except Exception as e: print('   ne-prod-admin.ne.ch DNS:',type(e).__name__)
tot=0
for p in (1,2):
    c,b,_=get(f'https://www.ne.ch/sitemap.xml?page={p}','application/xml'); n=len(re.findall(r'<loc>',b)); tot+=n; print(f'   page {p}:',c,n,'URLs')
print('   total',tot)
# 2 Romandie tenants external + tenant= counts
c,b,_=get('https://amtsblattportal.ch/api/v1/tenants','application/json'); T=json.loads(b)
for t in T:
    if t.get('id') in ('kabfr','kabvd','kabne','kabge','kabju'): print('[2 tenant]',t['id'],'external=',t.get('external'))
for t in ('kabvd','kabne'):
    c,b,_=get(f'https://amtsblattportal.ch/api/v1/publications?publicationStates=PUBLISHED&tenant={t}&pageRequest.size=50&pageRequest.page=0','application/json'); d=json.loads(b)
    print('[2 count]',t,c,'total=',d.get('total'),'| rubrics in first 50:',sorted(set(it['meta']['rubric'] for it in d['content'])))
# 3 Lausanne 193
c,b,_=get('https://www.lausanne.ch/apps/actualites/index_recueil.php','text/html')
m=re.search(r'(\d+)\s*r[ée]sultats',b); ids=set(re.findall(r'serve\.php\?id=(\d+)&(?:amp;)?kind=recueil',b))
print('[3 Lausanne]',c,'label:',m.group(0) if m else None,'| distinct ids',len(ids))
# 4 Ville de Genève pages 0 and 24/25
for p in (0,24,25):
    c,b,_=get(f'https://www.geneve.ch/autorites-administration/administration-municipale/reglements-municipaux?page={p}','text/html')
    print(f'[4 Geneve page {p}]',c,'LC links',len(set(re.findall(r'/reglements-municipaux/(lc[\w-]+)',b))))
# 5 La Chaux-de-Fonds POST API
c,b,_=get('https://www.chaux-de-fonds.ch/Api/Page.svc/detail','application/json',data=json.dumps({'page':'/rapports-et-reglements/reglementation'}))
try:
    d=json.loads(b)['DetailResult']; s=json.dumps(d,ensure_ascii=False)
    print('[5 LCdF API]',c,'title',d.get('Title'),'| theme links',len(set(re.findall(r'/rapports-et-reglements/reglementation/[\w-]+',s))),'| pdf refs',len(set(re.findall(r'Documents/[\w.]+\.pdf',s))))
except Exception as e: print('[5 LCdF API]',c,b[:200])
# 6 FR ICS
c,b,_=get('https://www.fr.ch/document/508696','text/calendar')
print('[6 FR ICS]',c,'VEVENTs',b.count('BEGIN:VEVENT'),'| autumn 2026 DTSTART 20261012:', 'DTSTART;VALUE=DATE:20261012' in b)
# 7 opencaselaw FR/VD
oc=json.load(open(S+'/opencaselaw_courts_2026-09-23.json'))
for it in oc:
    if it['court'] in ('fr_gerichte','vd_findinfo','vd_gerichte','vd_omni'): print('[7 opencaselaw]',it['court'],it['decision_count'],it['latest'])
# 8 GE FAO captcha, gazette robots
c,b,eff=get('https://fao.ge.ch/','text/html'); print('[8 fao.ge.ch]',c,eff,'| captcha text:', 'CAPTCHA' in b.upper())
for h in ('faovd.ch','www.faovd.ch','fo.fr.ch','rsju.jura.ch'):
    c,b,_=get(f'https://{h}/robots.txt','text/plain'); dis=re.findall(r'(?im)^Disallow:\s*(\S*)',b)
    print(f'[8 robots {h}]',c,'Disallow lines',len(dis),'| blocks /archive:',any(x.startswith('/archive') for x in dis),'| Disallow: / :', '/' in dis)
# 9 Vernier back up?
c,b,_=get('https://www.vernier.ch/administration-et-autorites/reglements-communaux','text/html'); print('[9 Vernier]',c,len(b),'bytes')
