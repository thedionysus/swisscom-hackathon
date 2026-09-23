S=<scratchpad>
python3 - "$S" <<'E'
import json,sys,collections
S=sys.argv[1];res=json.load(open(f'{S}/courts_s1_probe.json'))
for k in ('http-403','http-429','http-500'):
    print('==',k);[print('  ',('[D] ' if r['grounded'] else '[G] ')+u[:100],'->',r['final'][:70]) for u,r in res.items() if r['class']==k]
E
echo "== DNS for hosts that gave no response"
for h in gerichte-zg.ch gerichte.tg.ch tribunaux.vs.ch www.vg.justice.be.ch justiz-gr.ch www.justiz-gr.ch justice.ge.ch; do printf "%-24s " $h; dig +short $h | head -1 | sed 's/^$/NXDOMAIN or no A record/'; [ -z "$(dig +short $h)" ] && echo "(no answer)"; done
