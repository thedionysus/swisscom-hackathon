import json, subprocess
UA = 'Mozilla/5.0 swiss-grounding-check'
for t in ['kabti', 'kabgr', 'kabvs']:
    for start in ['2026-09-01', '2020-01-01']:
        u = (f'https://amtsblattportal.ch/api/v1/publications?publicationStates=PUBLISHED&tenants={t}'
             f'&publicationDate.start={start}&pageRequest.size=3&pageRequest.page=0')
        r = subprocess.run(['curl', '-sL', '--compressed', '--max-time', '60', '-A', UA, '-H', 'Accept: application/json', u],
                           capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
        except Exception:
            print(t, start, 'non-JSON', r.stdout[:200]); continue
        tot = d.get('total')
        print(t, 'since', start, 'total', tot)
        for p in (d.get('content') or [])[:3]:
            m = p.get('meta', {})
            ti = m.get('title', {})
            print('   ', m.get('publicationDate'), m.get('rubric'), m.get('subRubric'), '|', (ti.get('it') or ti.get('de') or ti.get('fr') or '')[:90],
                  '| office BFS', (m.get('registrationOffice') or {}).get('municipalityId'), '| id', m.get('id'))
