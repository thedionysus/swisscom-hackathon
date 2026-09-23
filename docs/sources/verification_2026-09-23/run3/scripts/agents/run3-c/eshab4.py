import subprocess, json, sys, collections
host=sys.argv[1]; q=sys.argv[2]
u=f'https://{host}/api/v1/publications?publicationStates=PUBLISHED&pageRequest.page=0&pageRequest.size=200&{q}'
d=json.loads(subprocess.run(['curl','-sL','--max-time','60','-A','Mozilla/5.0 swiss-grounding-check','-H','Accept: application/json',u],capture_output=True,text=True).stdout)
c=collections.Counter(it['meta'].get('rubric') for it in d['content'])
print(q,'total',d['total'],'rubrics first 200:',c.most_common(12))
