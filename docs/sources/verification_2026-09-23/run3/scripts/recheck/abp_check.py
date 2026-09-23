import json, subprocess
base='https://amtsblattportal.ch/api/v1/publications?publicationStates=PUBLISHED&publicationDate.start=2026-09-01&pageRequest.size=1&pageRequest.page=0'
for q in ['', '&cantons=TI', '&cantons=VS', '&tenants=kabti', '&tenants=kabvs']:
    r=subprocess.run(['curl','-sL','--compressed','--max-time','60','-A','Mozilla/5.0 swiss-grounding-check','-H','Accept: application/json','-w','\n%{http_code}',base+q],capture_output=True,text=True)
    body,code=r.stdout.rsplit('\n',1)
    try: tot=json.loads(body).get('total')
    except Exception: tot='non-JSON '+body[:80]
    print(f'{q or "(no filter)":16} HTTP {code}  total={tot}')
