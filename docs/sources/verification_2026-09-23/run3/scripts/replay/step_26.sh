S=<scratchpad>
python3 - "$S" <<'E'
import json,sys,re,collections
S=sys.argv[1]
t=open(f'{S}/precheck_entry_points_2026-09-23.md').read()
res=json.load(open(f'{S}/s3b_s4_probe.json'))
add=collections.defaultdict(list)
for r in res:
    if r['cls'] in('ok','redirect','redirect-to-home'):
        add[r['canton']].append(f"- [{r['topic']} ({r['src']})] {r['final'].replace(':443','')} — {r['title'][:50]}")
blk=t.split('## Blocked / invented (do not retry)')
body,tail=blk[0],blk[1]
for c in sorted(add):
    if f'## {c} ' in body:
        body=re.sub(rf'(## {c} [^\n]*\n(?:- [^\n]*\n)*)',lambda m:m.group(1)+'\n'.join(add[c])+'\n',body,count=1)
    else:
        body=body.rstrip('\n')+f'\n\n## {c}\n'+'\n'.join(add[c])+'\n'
tail=tail.replace('- sh.ch: invented CMS ids answer 500; old desktopdefault.aspx ids redirect to the home page',
 '- sh.ch is up (home and road-office pages answer 200). Unknown page ids answer 500 with a CMS error page titled "Maintenance Page". Old desktopdefault.aspx ids redirect to the home page')
tail=tail.replace('- Invented domains (no DNS): gerichte-zg.ch, gerichte.tg.ch, tribunaux.vs.ch, www.vg.justice.be.ch, justiz-gr.ch',
 '- Invented or obsolete domains (no DNS): gerichte-zg.ch, gerichte.tg.ch, tribunaux.vs.ch, www.vg.justice.be.ch, justiz-gr.ch, www.jgk.be.ch, gem.lu.ch, bare tg.ch (use www.tg.ch)')
tail+='''
- www.ge.ch/dossier/communes-genevoises answered 403 (redirect to /taxonomy/term/3084)
- Portal structure hints taken from 404 redirects:
  - jura.ch pages live under /fr/Autorites/Administration/<DEPT>/<SERVICE>/…
  - vd.ch dropped the /themes/ prefix; the real pages are elsewhere, e.g. /mobilite/automobile-et-navigation
  - vs.ch services live at /web/<service>, e.g. /web/scc, /web/scn, /web/che
- Summary of the S3b/S4 check (plain-text links, no Gemini wrapper signal): 20 of 76 usable (26%)
'''
open(f'{S}/precheck_entry_points_2026-09-23.md','w').write(body+'## Blocked / invented (do not retry)'+tail)
n=sum(1 for l in (body).splitlines() if l.startswith('- ['))
cant=len([l for l in body.splitlines() if l.startswith('## ') and not l.startswith('## cities')])
print('verified entry points:',n,'across',cant,'cantons (+ cities section)')
missing=sorted(set('ZH BE LU UR SZ OW NW GL ZG FR SO BS BL SH AR AI SG GR AG TG TI VD VS NE GE JU'.split())-{l.split()[1] for l in body.splitlines() if l.startswith('## ') and not l.startswith('## cities')})
print('cantons with no verified entry point yet:',missing)
E
