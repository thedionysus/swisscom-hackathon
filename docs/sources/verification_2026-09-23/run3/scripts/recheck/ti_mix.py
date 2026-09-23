import json, subprocess, collections
UA='Mozilla/5.0 swiss-grounding-check'
for canton in ['TI','VS']:
    u=f'https://amtsblattportal.ch/api/v1/publications?publicationStates=PUBLISHED&cantons={canton}&publicationDate.start=2026-09-01&pageRequest.page=0&pageRequest.size=500'
    r=subprocess.run(['curl','-s','--compressed','--max-time','90','-A',UA,'-H','Accept: application/json',u],capture_output=True,text=True)
    d=json.loads(r.stdout)
    c=collections.Counter(it['meta'].get('primaryTenantCode') for it in d['content'])
    print(canton,'total',d.get('total'),'| sample of',len(d['content']),'by tenant:',dict(c.most_common()))
