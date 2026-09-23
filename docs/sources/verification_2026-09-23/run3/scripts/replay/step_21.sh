S=<scratchpad>; cp <scratchpad>/sgchk/courts.json $S/opencaselaw_courts_2026-09-23.json
python3 - <<'E'
import json,collections
d=json.load(open('<scratchpad>/sgchk/courts.json'))
print('court entries',len(d),'total decisions',sum(x['decision_count'] for x in d))
by=collections.defaultdict(list)
for x in d: by[x['canton']].append(x)
for c in sorted(by):
    L=sorted(by[c],key=lambda x:-x['decision_count'])
    print(f"{c:3} {len(L):2} courts {sum(x['decision_count'] for x in L):7}  latest {max(x['latest'] or '' for x in L)}  | "+', '.join(f"{x['court']}({x['decision_count']})" for x in L[:6])+(' …' if len(L)>6 else ''))
missing=sorted(set('ZH BE LU UR SZ OW NW GL ZG FR SO BS BL SH AR AI SG GR AG TG TI VD VS NE GE JU'.split())-set(by))
print('cantons with no court in opencaselaw:',missing or 'none')
stale=[(x['court'],x['latest']) for x in d if x['canton']!='CH' and (x['latest'] or '')<'2026-01-01']
print('cantonal courts whose latest decision is before 2026:',len(stale),stale[:12])
E
