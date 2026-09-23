"""eSHAB API probe. usage: eshab.py HOST"""
import sys, subprocess, json
host=sys.argv[1]
def get(u):
    r=subprocess.run(['curl','-sL','--max-time','40','-A','Mozilla/5.0 swiss-grounding-check','-H','Accept: application/json','-w','\n%{http_code} %{content_type}',u],capture_output=True,text=True)
    b,meta=r.stdout.rsplit('\n',1); return meta,b
for path in ['/api/v1/current-tenant','/api/v1/publications?publicationStates=PUBLISHED&pageRequest.page=0&pageRequest.size=3']:
    meta,b=get(f'https://{host}{path}')
    print(path,'->',meta,len(b))
    try:
        d=json.loads(b)
        if isinstance(d,dict):
            print('  keys:',list(d.keys())[:15])
            if 'content' in d:
                print('  total:',d.get('total') or d.get('totalElements'),'| first item keys:',list(d['content'][0].keys())[:15] if d['content'] else None)
                for it in d['content'][:3]:
                    m=it.get('meta',it)
                    print('   ',m.get('publicationNumber'),m.get('publicationDate'),m.get('rubric'),m.get('subRubric'),'|',str(m.get('title'))[:120])
            else:
                print('  ',json.dumps(d,ensure_ascii=False)[:400])
    except Exception as e:
        print('  not json',b[:200])
