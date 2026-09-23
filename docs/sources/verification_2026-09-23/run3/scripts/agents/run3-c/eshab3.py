import subprocess, json, sys, collections
host,tenant=sys.argv[1],sys.argv[2]
u=f'https://{host}/api/v1/publications?publicationStates=PUBLISHED&pageRequest.page=0&pageRequest.size=200&tenant={tenant}'
d=json.loads(subprocess.run(['curl','-sL','--max-time','60','-A','Mozilla/5.0 swiss-grounding-check','-H','Accept: application/json',u],capture_output=True,text=True).stdout)
c=collections.Counter(it['meta'].get('rubric') for it in d['content'])
print(tenant,'total',d['total'],'rubrics in first 200:',c.most_common())
for it in d['content']:
    m=it['meta']
    if m.get('rubric')!='HR':
        print('  sample non-HR:',m.get('publicationNumber'),m.get('publicationDate','')[:10],m.get('rubric'),m.get('subRubric'),'|',(m.get('title') or {}).get('de','')[:100]); break
