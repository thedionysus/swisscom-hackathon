"""usage: lexindex.py HOST REGEX -- grep LexWork lightweight_index titles (dict of category lists or list)"""
import sys, subprocess, json, re
host,rx=sys.argv[1],re.compile(sys.argv[2],re.I)
u=f'https://{host}/api/de/texts_of_law/lightweight_index'
r=subprocess.run(['curl','-sL','--max-time','60','-A','Mozilla/5.0 swiss-grounding-check',u],capture_output=True,text=True)
d=json.loads(r.stdout)
items=[]
if isinstance(d,dict):
    for v in d.values():
        if isinstance(v,list): items+=v
else: items=d
print(host,'index items',len(items))
for it in items:
    t=it.get('title') or ''
    if rx.search(t):
        print('  ',it.get('systematic_number'),'|',t[:130],'| abrogated' if it.get('abrogated') else '')
