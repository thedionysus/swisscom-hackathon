import json,sys
SP='<scratchpad>'
d=json.load(open(SP+'/stage0/sitemap_topic_candidates.json'))
cantons=sys.argv[1].split(',')
nmax=int(sys.argv[2])
skip=sys.argv[3].split(',') if len(sys.argv)>3 else []
for c in cantons:
    v=d.get(c)
    print('=====',c, {t:x.get('count') for t,x in v.items()})
    for t,x in v.items():
        if t in skip: continue
        print('--',t,x.get('count'))
        for u in x.get('shortest',[])[:nmax]:
            if 'ftw-' in u: continue
            print('   ',u[:160])
