S=<scratchpad>
python3 - "$S" <<'E'
import json,sys,collections
S=sys.argv[1]
c1=json.load(open(f'{S}/courts_s1_probe.json'));sys.path.insert(0,S)
from courts_s1_rows import ROWS
g=json.load(open(f'{S}/guidance_s3a_probe.json'))
seed=collections.defaultdict(list);dead=collections.Counter()
url2canton={}
for r in ROWS:
    for cell in r[2:]: url2canton.setdefault(cell[2:],r[0])
generic={'https://www.bs.ch/willkommen-bei-den-gerichten','https://www.sg.ch/recht/gerichte.html','https://sh.ch/CMS/Webseite/Kanton-Schaffhausen-1756-DE.html'}
for u,r in c1.items():
    c=url2canton[u]
    if r['class'] in('ok','redirect-elsewhere','redirect-to-home') and r['size']>100:
        tag='courts'+(' (id-routed: same page for any path)' if 'gl.ch' in u else '')
        seed[c].append((tag,r['final'],r['title'][:45]))
    else: dead[c]+=1
for r in g:
    if r['cls'] in('ok','redirect') and r['final'] not in generic:
        seed[r['canton'] if r['canton']!='city-real' else 'cities'].append((r['topic'],r['final'],r['title'][:45]))
# de-duplicate
lines=['# Pre-check 2026-09-23: verified entry points per canton (input for the agents)','',
 'Built from one live request per link. S1 courts: 141 links. S2 cities: 10 links, all 404; real pages came from G1 saved homepages. S3a guidance: 64 links.',
 'Only pages that answered 200 with real content are listed. Gemini-wrapped links that failed are not listed: agents must not retry them.','']
for c in sorted(seed):
    L=list(dict.fromkeys(seed[c]))
    lines.append(f'## {c}  ({len(L)} verified entry points; {dead[c]} dead AI court links)')
    for t,u,ti in L: lines.append(f'- [{t}] {u} — {ti}')
    lines.append('')
lines+=['## Blocked / invented (do not retry)',
 '- Invented domains (no DNS): gerichte-zg.ch, gerichte.tg.ch, tribunaux.vs.ch, www.vg.justice.be.ch, justiz-gr.ch',
 '- www.baselland.ch: Cloudflare challenge ("Just a moment…", HTTP 403) for our client. Use bl.clex.ch (LexWork) and data.bl.ch (ODS); report the rest as blocked',
 '- www.sz.ch and www.gl.ch answered 429: throttle to ≥3 s between requests',
 '- sh.ch: invented CMS ids answer 500; old desktopdefault.aspx ids redirect to the home page',
 '- gl.ch routes by the trailing numeric id: any path ending in /720 shows the same page. Always check the <title>',
 '- vgrzh.djiktzh.ch answered 200 with a 4-byte body: JS app or empty; needs a look']
open(f'{S}/precheck_entry_points_2026-09-23.md','w').write('\n'.join(lines))
print('\n'.join(lines))
E
