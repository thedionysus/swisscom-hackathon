import json
SP='<scratchpad>'
d=json.load(open(SP+'/stage0/law_hits.json'))
for c in ['SG','TG','AR','AI','SH']:
    print('=====',c)
    v=d.get(c)
    if isinstance(v,dict):
        for t,items in v.items():
            if isinstance(items,list):
                for it in items:
                    print(f"  {t:13} {it.get('nr') or it.get('id')} | {(it.get('title') or '')[:110]} | {it.get('api') or it.get('url')}")
            else:
                print('  ',t,str(items)[:300])
    else:
        print(str(v)[:1000])
