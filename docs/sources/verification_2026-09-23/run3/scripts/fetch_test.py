import glob, os, sys, time, json, csv
from urllib.parse import urlparse
import httpx
from swiss_grounding.config import Settings
from swiss_grounding.registry.loader import load_source_yaml
from swiss_grounding.ingest.fetchers import build_fetcher
R=sys.argv[1]
settings=Settings(database_url='postgresql://unused/unused', crawl_max_pages=2, crawl_delay_seconds=1.0)
SLOW={'www.sz.ch':5,'www.gl.ch':5,'sz.ch':5,'gl.ch':5}
last={}; results={}
for p in sorted(glob.glob(f'{R}/ready_sources/*.yaml')):
    src=load_source_yaml(open(p).read())
    if src.fetch_strategy.value=='pdf':
        first=src.fetch_config['urls'][0]
        try:
            h=httpx.head(first,follow_redirects=True,timeout=20,headers={'user-agent':settings.user_agent})
            size=int(h.headers.get('content-length') or 0)
        except Exception: size=0
        if size>20_000_000:
            results[src.id]={'docs':None,'errors':0,'note':f'skipped: first PDF is {size//1_000_000} MB'}; continue
        src=src.model_copy(update={'fetch_config':{**src.fetch_config,'urls':[first]}})
    host=urlparse(src.base_url).netloc; wait=SLOW.get(host,1.0)-(time.time()-last.get(host,0))
    if wait>0: time.sleep(wait)
    t0=time.time()
    try:
        r=build_fetcher(src.fetch_strategy, settings).fetch(src, {})
        d=r.documents[0] if r.documents else None
        results[src.id]={'docs':len(r.documents),'errors':len(r.errors),
            'first_error':(r.errors[0].reason[:120] if r.errors else ''),
            'sample_title':(d.title[:90] if d else ''),'sample_sections':(len(d.sections) if d and getattr(d,'sections',None) is not None else None),
            'seconds':round(time.time()-t0,1)}
    except Exception as ex:
        results[src.id]={'docs':0,'errors':1,'first_error':f'{type(ex).__name__}: {str(ex)[:120]}'}
    last[host]=time.time()
    print(src.id, results[src.id], flush=True)
json.dump(results,open(f'{R}/../run3_fetch_test.json','w'),ensure_ascii=False,indent=1)
ok=sum(1 for v in results.values() if v.get('docs'))
print('SUMMARY sources',len(results),'| with >=1 document',ok,'| zero documents',sum(1 for v in results.values() if v.get('docs')==0),'| skipped',sum(1 for v in results.values() if v.get('docs') is None))
