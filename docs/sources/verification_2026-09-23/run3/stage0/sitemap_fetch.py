import sys,re,json,gzip,time,subprocess,threading,collections,concurrent.futures as cf
S=sys.argv[1];UA='Mozilla/5.0 swiss-grounding-check'
HOSTS={
'ZH':['www.zh.ch','www.gerichte-zh.ch','www.stadt-zuerich.ch'],
'BE':['www.zsg.justice.be.ch','www.rsta.dij.be.ch','www.svsa.sid.be.ch','www.sv.fin.be.ch','www.weu.be.ch','www.bkd.be.ch','www.sta.be.ch','www.akvb-gemeinden.bkd.be.ch','www.be.ch','www.bern.ch','www.thun.ch'],
'LU':['www.lu.ch','gerichte.lu.ch','veterinaerdienst.lu.ch','steuerbuch.lu.ch','strassenverkehrsamt.lu.ch','volksschulbildung.lu.ch'],
'UR':['www.ur.ch'],'SZ':['www.sz.ch'],'OW':['www.ow.ch'],'NW':['www.nw.ch'],'GL':['www.gl.ch'],'ZG':['zg.ch'],
'FR':['www.fr.ch','www.ocn.ch'],'SO':['so.ch'],'BS':['www.bs.ch'],'BL':['www.baselland.ch'],'SH':['sh.ch','www.stadt-schaffhausen.ch'],
'AR':['ar.ch'],'AI':['www.ai.ch'],'SG':['www.sg.ch'],'GR':['www.gr.ch'],'AG':['www.ag.ch'],
'TG':['www.tg.ch','strassenverkehrsamt.tg.ch','staatskanzlei.tg.ch'],'TI':['www4.ti.ch','www.lugano.ch'],
'VD':['www.vd.ch','www.lausanne.ch'],'VS':['www.vs.ch'],'NE':['www.ne.ch','www.scan-ne.ch','www.chaux-de-fonds.ch','www.neuchatelville.ch'],
'GE':['www.ge.ch','justice.ge.ch','www.geneve.ch','www.vernier.ch'],'JU':['www.jura.ch'],
}
THROTTLE={'www.sz.ch':3,'www.gl.ch':3}
def get(url):
    r=subprocess.run(['curl','-sL','-g','--compressed','--max-time','60','-A',UA,'-w','\n%{http_code}',url],capture_output=True)
    body=r.stdout;code=body[-3:].decode(errors='ignore');body=body[:-4]
    if body[:2]==b'\x1f\x8b':
        try: body=gzip.decompress(body)
        except Exception: pass
    return code,body.decode('utf-8',errors='ignore')
def crawl(host):
    log=[];delay=THROTTLE.get(host,0.3)
    code,robots=get(f'https://{host}/robots.txt');log.append(f'robots {code}')
    m=re.search(r'(?im)^crawl-delay:\s*([\d.]+)',robots) if code=='200' else None
    if m: delay=max(delay,min(float(m.group(1)),10))
    maps=re.findall(r'(?im)^sitemap:\s*(\S+)',robots) if code=='200' else []
    if not maps: maps=[f'https://{host}/sitemap.xml',f'https://{host}/sitemap_index.xml']
    urls=set();seen=set();queue=list(maps);fetched=0
    while queue and fetched<80:
        sm=queue.pop(0)
        if sm in seen: continue
        seen.add(sm);time.sleep(delay);code,x=get(sm);fetched+=1
        locs=re.findall(r'<loc>\s*([^<\s]+)\s*</loc>',x)
        if '<sitemapindex' in x: queue+= [l.replace('&amp;','&') for l in locs]
        else: urls.update(l.replace('&amp;','&') for l in locs)
        log.append(f'{sm} {code} {len(locs)}')
    open(f'{S}/stage0/sitemaps/{host}.txt','w').write('\n'.join(sorted(urls)))
    return host,len(urls),fetched,delay,log[:3]
allhosts=[h for hs in HOSTS.values() for h in hs]
out={}
with cf.ThreadPoolExecutor(10) as ex:
    for host,n,f,delay,log in ex.map(crawl,allhosts):
        out[host]={'urls':n,'sitemaps_fetched':f,'delay':delay,'log':log}
        print(f'{host:34} urls {n:6} sitemaps {f:3} delay {delay:4} | {log[0]} | {log[1] if len(log)>1 else ""}',flush=True)
json.dump({'hosts':HOSTS,'result':out},open(f'{S}/stage0/sitemaps_summary.json','w'),indent=1)
