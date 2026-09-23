import yaml, re, glob, os, sys, json, csv, collections
from urllib.parse import urlparse
from swiss_grounding.registry.models import Source, FetchStrategy
from swiss_grounding.registry.categories import CATEGORY_IDS
from swiss_grounding.registry.loader import load_source_yaml
R=sys.argv[1]; OUT=f'{R}/ready_sources'; os.makedirs(OUT,exist_ok=True)
CANTONS='ZH BE LU UR SZ OW NW GL ZG FR SO BS BL SH AR AI SG GR AG TG TI VD VS NE GE JU'.split()
CITY_EXT={'stadt_zuerich':'CH-ZH-261','stadt_bern':'CH-BE-351','stadt_thun':'CH-BE-942','stadt_schaffhausen':'CH-SH-2939','lugano':'CH-TI-5192'}
DATATYPE={'html_crawl':'HTML pages (server-rendered)','pdf':'PDF documents (text layer)','api':'JSON API','fedlex_sparql':'SPARQL'}
rows=[]; seen=set()
for f in sorted(glob.glob(f'{R}/draft_sources/*.yaml')):
    agent=os.path.basename(f)[:6]; raw=open(f).read()
    for blk in raw.split('\n---\n'):
        hm=re.search(r'# ---- block \d+ · section: (.*?) · parses',blk); section=hm.group(1) if hm else ''
        sec_canton=next((t for t in re.findall(r'\b([A-Z]{2})\b',section) if t in CANTONS),None)
        try: docs=[d for d in yaml.safe_load_all(blk) if d is not None]
        except Exception: continue
        entries=[e for d in docs for e in (d if isinstance(d,list) else [d]) if isinstance(e,dict)]
        for e in entries:
            eid=str(e.get('id'))
            # comments near this entry: the id line and following lines until the next id
            m=re.search(r'^[ \-]*id:\s*'+re.escape(eid)+r'\b.*?(?=^[ \-]*id:|\Z)',blk,re.S|re.M)
            ctx=(m.group(0) if m else '')
            pre=re.search(r'((?:^#[^\n]*\n)+)[ \-]*id:\s*'+re.escape(eid)+r'\b',blk,re.M)
            comments=' '.join(re.findall(r'#([^\n]*)',ctx+(pre.group(1) if pre else '')))
            s=dict(e); filled=[]
            cfg=s.get('fetch_config') or {}
            urls=[u for k in ('url','urls','start_paths') for u in (cfg.get(k) if isinstance(cfg.get(k),list) else [cfg.get(k)] if cfg.get(k) else []) if isinstance(u,str) and u.startswith('http')]
            if 'base_url' not in s:
                if urls: s['base_url']='{0.scheme}://{0.netloc}'.format(urlparse(urls[0])); filled.append('base_url')
            if 'authority' not in s:
                a=next((x for x in ('official_info','institutional','municipal_law','cantonal_law') if x in comments),'official_info'); s['authority']=a; filled.append('authority')
            if 'default_extent_id' not in s:
                ext=re.search(r'\b(CH-[A-Z]{2}(?:-\d+)?)\b',comments)
                ext=ext.group(1) if ext else next((v for k,v in CITY_EXT.items() if eid.startswith(k)),None) or (f'CH-{sec_canton}' if sec_canton else None)
                if ext: s['default_extent_id']=ext; filled.append('default_extent_id')
            cats=s.get('categories') or []
            missing_cat=', '.join(sorted(set(re.findall(r'category missing: ([a-z_ ]+?)(?:[;,)|]|$|\s{2}|\s\(|\s—)',comments+' '))))
            if not cats:
                guess=[c for c in CATEGORY_IDS if re.search(r'(^|[\s|#,])'+c+r'([\s|,;)]|$)',comments)]
                if guess: s['categories']=guess; filled.append('categories')
            if 'name' not in s:
                words=re.sub(r'[-_]',' ',eid).split()
                s['name']=' '.join(w.upper() if w.upper() in CANTONS else w.capitalize() for w in words); filled.append('name')
            strategy=str(s.get('fetch_strategy'))
            ok=False; err=''
            try:
                Source.model_validate(s); ok=True
            except Exception as ex:
                err=str(ex).split('\n')[1] if '\n' in str(ex) else str(ex)
            ready = ok and strategy in {x.value for x in FetchStrategy}
            if ready:
                key=eid
                while key in seen: key+='_2'
                seen.add(key); s['id']=key
                order=['id','name','base_url','default_extent_id','authority','categories','fetch_strategy','fetch_config','allow_narrowing','llm_tagging','license']
                ordered={k:s[k] for k in order if k in s}; ordered.update({k:v for k,v in s.items() if k not in ordered})
                text=(f'# Draft from Run 3 ({agent}, section: {section}). Not yet in the registry.\n'
                      f'# Fields filled by the orchestrator from the agent\'s notes: {", ".join(filled) or "none"}.\n'
                      + (f'# Category missing in the registry: {missing_cat}\n' if missing_cat else '')
                      + yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=140))
                load_source_yaml(text)  # the pipeline's own loader must accept it
                open(f'{OUT}/{key}.yaml','w').write(text)
            rows.append({'id':s.get('id'),'agent':agent,'canton':sec_canton or '','name':s.get('name'),'default_extent_id':s.get('default_extent_id',''),
                'authority':s.get('authority',''),'categories':' '.join(s.get('categories') or []),'category_missing':missing_cat,
                'data_type':DATATYPE.get(strategy,f'needs new fetcher: {strategy}'),'fetch_strategy':strategy,
                'entry_points':' '.join(urls) or ' '.join(map(str,cfg.get('start_paths',[]) or [])),'base_url':s.get('base_url',''),
                'fetch_config':json.dumps(cfg,ensure_ascii=False),'fields_filled':' '.join(filled),
                'readiness':'ready: validates with registry loader' if ready else ('needs new fetcher' if ok or 'fetch_strategy' in err else 'invalid: '+err[:80]),
                'report':f'agent_reports/{agent}.md','notes':comments.strip()[:300]})
with open(f'{R}/source_catalogue.csv','w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
c=collections.Counter(r['readiness'].split(':')[0] for r in rows)
print('entries',len(rows),'| readiness',dict(c),'| ready yaml files',len(os.listdir(OUT)))
print('by strategy (ready):',dict(collections.Counter(r['fetch_strategy'] for r in rows if r['readiness'].startswith('ready'))))
print('categories empty among ready:',sum(1 for r in rows if r['readiness'].startswith('ready') and not r['categories']))
for r in rows:
    if not r['readiness'].startswith('ready'): print('  not ready:',r['id'],'|',r['readiness'])
