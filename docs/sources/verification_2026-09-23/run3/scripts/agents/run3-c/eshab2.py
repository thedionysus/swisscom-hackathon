import subprocess, json, sys
host=sys.argv[1]
base=f'https://{host}/api/v1/publications?publicationStates=PUBLISHED&pageRequest.page=0&pageRequest.size=3'
for extra in sys.argv[2:]:
    u=base+'&'+extra
    r=subprocess.run(['curl','-sL','--max-time','40','-A','Mozilla/5.0 swiss-grounding-check','-H','Accept: application/json',u],capture_output=True,text=True)
    try:
        d=json.loads(r.stdout)
        print(extra,'-> total',d.get('total'))
        for it in d.get('content',[])[:3]:
            m=it['meta']; print('    ',m.get('publicationNumber'),m.get('publicationDate','')[:10],m.get('cantons'),m.get('rubric'),'|',(m.get('title') or {}).get('de','')[:90])
    except Exception as e:
        print(extra,'-> not json',r.stdout[:150])
