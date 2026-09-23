S=<scratchpad>
python3 - "$S" <<'E'
import sys,json,subprocess,time
S=sys.argv[1];UA='Mozilla/5.0 swiss-grounding-check';B='https://www.lexfind.ch/api/fe'
def get(u): return subprocess.run(['curl','-sL','-g','--max-time','60','-A',UA,u],capture_output=True,text=True).stdout
ents=json.loads(get(f'{B}/de/entities'))
lst=ents if isinstance(ents,list) else ents.get('entities',ents)
def name(e): return json.dumps(e,ensure_ascii=False)
want={'ZH':['Zürich','Zurich'],'GE':['Genève','Genf','Geneva'],'VD':['Vaud','Waadt'],'NE':['Neuchâtel','Neuenburg'],'TI':['Ticino','Tessin'],'JU':['Jura']}
ids={}
for e in lst:
    s=name(e)
    for c,names in want.items():
        if c not in ids and any(n in s for n in names) and 'Intlex' not in s: ids[c]=e['id']
print('entity ids',ids)
for c,eid in ids.items():
    tree=json.loads(get(f'{B}/de/entities/{eid}/systematics'))
    nodes=[k for k in tree if k]
    tols=[]
    for i in range(0,len(nodes),100):
        q='&'.join(f'tols_for_systematics[]={n}' for n in nodes[i:i+100])
        d=json.loads(get(f'{B}/de/entities/{eid}/systematics?active_only=true&{q}'))
        for k,v in d.items():
            for t in (v.get('tols') or []): tols.append(t)
        time.sleep(0.5)
    uniq={t['id']:t for t in tols}
    json.dump({'lexfind_entity':eid,'items':list(uniq.values())},open(f'{S}/stage0/laws_{c}.json','w'),ensure_ascii=False)
    print(f'{c} entity {eid}: nodes {len(nodes)}, texts {len(uniq)}')
E
