import json, subprocess, re, sys, os, collections
S=sys.argv[1]; UA='Mozilla/5.0 swiss-grounding-check'; JAR=S+'/recheck/lexican.jar'
def get(u, acc='application/json', jar=False):
    cmd=['curl','-s','-g','-L','--compressed','--max-time','60','-A',UA,'-H','Accept: '+acc,'-w','\n%{http_code}']
    if jar: cmd+=['-c',JAR,'-b',JAR]
    r=subprocess.run(cmd+[u],capture_output=True,text=True); b,c=r.stdout.rsplit('\n',1); return c,b
# 1 sh.ch page is a JS shell; CMS JSON endpoint returns the text
c,b=get('https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Verwaltung/Departement-des-Innern/Veterin-ramt-1575596-DE.html','text/html')
vis=re.sub(r'<script.*?</script>|<style.*?</style>','',b,flags=re.S); vis=re.sub(r'<[^>]+>',' ',vis)
print('[1 sh.ch page]',c,'visible words',len(vis.split()),'| CONTENT_DATA embedded:', 'CONTENT_DATA' in b)
c,b=get('https://sh.ch/CMS/content?contentid=1575596&language=DE')
try:
    d=json.loads(b); d0=d[0] if isinstance(d,list) else d
    txt=re.sub(r'<[^>]+>',' ',str(d0.get('data_post_content','')))
    print('[1 sh CMS JSON]',c,'keys:',[k for k in d0 if k.startswith('data_')][:8],'| AMICUS sentence:', bool(re.search(r'AMICUS',txt)))
except Exception as e: print('[1 sh CMS JSON]',c,b[:150])
# 2 lexiCan outline (session cookie first)
if os.path.exists(JAR): os.remove(JAR)
c,b=get('https://sh.lexican.cloud/Project/Details/KArfO5bFd0CkaahGqsNmbQ/article/aoFNqnTRdogvkpgo','text/html',jar=True)
c2,b2=get('https://sh.lexican.cloud/api/OutlineApi/full?projectId=KArfO5bFd0CkaahGqsNmbQ',jar=True)
try:
    d=json.loads(b2); n=[0,0]
    def walk(x):
        for it in (x if isinstance(x,list) else [x]):
            n[0]+=1; ch=it.get('ChildArticles') or []
            if not ch: n[1]+=1
            walk(ch) if ch else None
    walk(d); print('[2 lexiCan]',c,c2,'nodes',n[0],'leaves',n[1])
except Exception as e: print('[2 lexiCan]',c,c2,b2[:150])
# 3/4 TG sitemaps
def locs(u):
    c,b=get(u,'application/xml'); L=re.findall(r'<loc>([^<]+)</loc>',b); return c,L
for host in ['steuerpraxis.tg.ch','rechtsprechung.tg.ch']:
    c,L=locs(f'https://{host}/sitemap.xml'); allu=[]
    for u in L:
        if u.endswith('.xml'): allu+=locs(u)[1]
        else: allu.append(u)
    extra=''
    if host.startswith('steuer'): extra='| 2026-09: '+str(sum('/2026-09/' in u for u in allu))+' | versions: '+str(sorted(set(re.findall(r'/steuerpraxis/(\d{4}-\d{2})',' '.join(allu)))))
    print(f'[3/4 {host}]',c,'children',len(L),'urls',len(allu),extra)
# 5 opencaselaw TG/SH
oc=json.load(open(S+'/opencaselaw_courts_2026-09-23.json'))
for it in (oc if isinstance(oc,list) else oc.get('courts',[])):
    if it['court'] in ('tg_obergericht','tg_gerichte','sh_obergericht','sh_gerichte','sg_publikationen','sg_handelsgericht'): print('[5 opencaselaw]',it['court'],it['decision_count'],it['latest'])
# 6 Stadt Schaffhausen i-web table
c,b=get('https://www.stadt-schaffhausen.ch/rechtssammlung','text/html')
m=re.search(r'data-entities="([^"]+)"',b)
if m:
    import html as H; ent=json.loads(H.unescape(m.group(1))); rows=ent.get('data',ent) if isinstance(ent,dict) else ent
    s=json.dumps(rows,ensure_ascii=False)
    print('[6 Stadt SH]',c,'rows',len(rows),'| 353.2 present:', '353.2' in s, '| 740.1 present:','740.1' in s)
else: print('[6 Stadt SH]',c,'no data-entities')
# 7 AR cantonal dog tax
c,b=get('https://ar.ch/verwaltung/departement-gesundheit-und-soziales/veterinaeramt/hunde/hundesteuer/','text/html'); t=re.sub(r'<[^>]+>',' ',b)
m=re.search(r'jährliche Hundesteuer[^.]{0,60}',t); print('[7 AR dog tax]',c, m.group(0) if m else 'NOT FOUND')
# 8 gazette 401 isolation: same client, with and without publicationStates
for q in ['publicationStates=PUBLISHED&','']:
    c,b=get(f'https://amtsblattportal.ch/api/v1/publications?{q}cantons=AR&pageRequest.size=1&pageRequest.page=0')
    print(f'[8 amtsblattportal {"with" if q else "without"} publicationStates]',c)
# 9 publikationen.sg.ch robots
c,b=get('https://publikationen.sg.ch/robots.txt','text/plain'); print('[9 publikationen.sg.ch robots]',c, re.findall(r'User-agent: \*\s*\n\s*Disallow: *(\S*)',b), '| named agents:',re.findall(r'User-agent: (\S+)',b)[:6])
# 10 law_hits SH court fees
lh=json.load(open(S+'/stage0/law_hits.json')); sh=lh.get('SH',{})
print('[10 law_hits SH court_fees]', json.dumps(sh.get('court_fees',[]),ensure_ascii=False)[:300])
