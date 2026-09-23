import json, re, os, sys, shutil, glob, csv
import yaml
NEW=sys.argv[1]; WT=sys.argv[2]
D=f'{WT}/docs/sources/verification_2026-09-23/run3'
for sub in ['agent_reports','stage0/precheck','scripts/replay','scripts/recheck','scripts/agents','inputs_restored','overnight_digests','draft_sources']:
    os.makedirs(f'{D}/{sub}',exist_ok=True)
# 1 agent reports (final) + first versions of A and D
for x in 'abcde': shutil.copy(f'{NEW}/reports/run3-{x}.md', f'{D}/agent_reports/run3-{x}.md')
for x,tid in [('a','a7b644d83e8577fde'),('d','a731a7220c822138d')]:
    rows=[json.loads(l) for l in open(f'{NEW}/../tasks/{tid}.output')]
    longs=[''.join(y.get('text','') for y in r['message'].get('content',[]) if y.get('type')=='text') for r in rows if r.get('type')=='assistant']
    longs=[t for t in longs if len(t)>5000]
    open(f'{D}/agent_reports/run3-{x}_v1.md','w').write(longs[0])
shutil.copy(f'{NEW}/run3_consolidated_2026-09-23.md', f'{D}/consolidated_report.md')
shutil.copy(f'{NEW}/agent_brief_v5.md', f'{D}/agent_brief_v5.md')
# 2 stage0 inputs (not the 50 MB sitemaps)
for f in glob.glob(f'{NEW}/stage0/*.json')+[f'{NEW}/stage0/sitemap_fetch.py']: shutil.copy(f, f'{D}/stage0/')
for f in ['precheck_entry_points_2026-09-23.md','opencaselaw_courts_2026-09-23.json','courts_s1_rows.py','courts_s1_probe.json','guidance_s3a_rows.py','guidance_s3a_probe.json','s3b_s4_rows.py','s3b_s4_probe.json','cities_s2_links.txt']:
    shutil.copy(f'{NEW}/{f}', f'{D}/stage0/precheck/')
# 3 scripts
for f in glob.glob(f'{NEW}/replay/step_*.sh')+[f'{NEW}/replay/run_all.sh', f'{NEW}/replay/run_all.log']: shutil.copy(f, f'{D}/scripts/replay/')
for f in glob.glob(f'{NEW}/recheck/*.py'): shutil.copy(f, f'{D}/scripts/recheck/')
shutil.copy(f'{NEW}/build_run3_commit.py', f'{D}/scripts/')
for x in 'abcde':
    os.makedirs(f'{D}/scripts/agents/run3-{x}',exist_ok=True)
    for f in glob.glob(f'{NEW}/run3-{x}/*.py'): shutil.copy(f, f'{D}/scripts/agents/run3-{x}/')
# 4 restored overnight inputs + digests of the stalled overnight agents
for f in glob.glob(f'{NEW}/restored/*'): shutil.copy(f, f'{D}/inputs_restored/')
for f in glob.glob(f'{NEW}/prior_run3/*.md'): shutil.copy(f, f'{D}/overnight_digests/')

# 5 confirmed_links.csv from the grid tables
CANTONS='ZH BE LU UR SZ OW NW GL ZG FR SO BS BL SH AR AI SG GR AG TG TI VD VS NE GE JU'.split()
CITY={'Zürich':'ZH','Bern':'BE','Thun':'BE','Lausanne':'VD','Neuchâtel':'NE','La Chaux-de-Fonds':'NE','Genève':'GE','Vernier':'GE','Schaffhausen':'SH','Lugano':'TI'}
ABS=re.compile(r'https?://[^\s`\'"<>\]\)|,;]+')
def cells(line): return [c.strip() for c in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
out=[]
for x in 'abcde':
    lines=open(f'{D}/agent_reports/run3-{x}.md').read().splitlines()
    canton=None; base=None; header=None; heading=''
    for i,l in enumerate(lines):
        if l.startswith('## '):
            heading=l[3:].strip(); toks=re.findall(r'\b([A-Z]{2})\b',heading)
            canton=next((t for t in toks if t in CANTONS),None)
            m=re.search(r'\(base (https?://[^\s;)]+)',heading); base=m.group(1) if m else None; header=None; continue
        if l.startswith('|') and i+1<len(lines) and re.match(r'^\|\s*:?-{3}',lines[i+1]): header=cells(l); continue
        if not (l.startswith('|') and header) or re.match(r'^\|\s*:?-{3}',l): 
            if not l.startswith('|'): header=None if l.strip()=='' and False else header
            continue
        row=cells(l); h0=header[0].lower()
        if len(row)<3: continue
        city=None
        if h0.startswith('cell') and not (len(header)>1 and 'status' in header[1].lower()): continue
        if h0.startswith('cell'):
            m=re.match(r'^\**\s*(C[1-5]|G[1-4]|D[12]|L1)\b(.*)$',row[0])
            if not m: continue
            cell=m.group(1)
            if cell=='L1':
                rest=re.sub(r'[*]','',m.group(2)).strip(); city=next((c for c in CITY if c in rest or c in heading),None)
        elif h0.startswith('city'):
            cell='L1'; name=re.sub(r'[*]','',row[0]); city=next((c for c in CITY if c in name),name.strip())
        else: continue
        cn=CITY.get(city,canton) if cell=='L1' and city in CITY else canton
        rec={'agent':f'run3-{x}','canton':cn,'cell':cell,'city':city or '','status':'','urls':'','urls_elsewhere_in_row':'','url_cell':'','evidence':'','sample':'','notes':'','section':heading}
        extra=[]
        for hname,val in zip(header,row):
            hl=hname.lower()
            if hl.startswith('status'): rec['status']=val
            elif 'url' in hl or 'location' in hl: rec['url_cell']=val
            elif hl.startswith('evidence') or hl.startswith('platform'): rec['evidence']=(rec['evidence']+' | ' if rec['evidence'] else '')+val
            elif hl.startswith('sample'): rec['sample']=val
            elif hl.startswith('cell') or hl.startswith('city'): pass
            else: extra.append(f'{hname}: {val}')
        rec['notes']=' || '.join(extra)
        # URL extraction: absolute URLs; backticked relative paths resolved against the last host in the cell (or the section base)
        urls=[]; host=base
        for tok in re.finditer(r'`([^`]+)`|(https?://[^\s`\'"<>\]\)|,;]+)',rec['url_cell']):
            s=(tok.group(1) or tok.group(2)).strip()
            for a in ABS.findall(s):
                a=a.rstrip('.'); urls.append(a); host=re.match(r'https?://[^/]+',a).group(0)
            if tok.group(1) and s.startswith('/') and host:
                urls.append(host+s.split()[0])
        rec['urls']=' '.join(dict.fromkeys(urls))
        other=[a.rstrip('.') for k in ('evidence','sample','notes') for a in ABS.findall(rec[k])]
        rec['urls_elsewhere_in_row']=' '.join(u for u in dict.fromkeys(other) if u not in urls)
        out.append(rec)
with open(f'{D}/confirmed_links.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
import collections
cnt=collections.Counter((r['canton'],r['cell']) for r in out)
print('csv rows',len(out),'| cantons',len({r['canton'] for r in out}),'| L1 rows',sum(1 for r in out if r['cell']=='L1'),'| rows without any URL',sum(1 for r in out if not r['urls']))
print('rows per canton:',dict(collections.Counter(r['canton'] for r in out)))

# 6 draft YAMLs, validated
summary=[]
for x in 'abcde':
    text=open(f'{D}/agent_reports/run3-{x}.md').read()
    blocks=[]; heading=''
    for m in re.finditer(r'^## ([^\n]*)$|```yaml\n(.*?)```',text,re.S|re.M):
        if m.group(1) is not None: heading=m.group(1).strip(); continue
        b=m.group(2)
        try: docs=[d for d in yaml.safe_load_all(b) if d is not None]; ok=True; n=sum(len(d) if isinstance(d,list) else 1 for d in docs)
        except Exception as e: ok=False; n=0
        blocks.append((heading,b,ok,n))
    with open(f'{D}/draft_sources/run3-{x}.yaml','w') as f:
        f.write(f'# Draft source configs proposed by agent run3-{x} on 2026-09-23. NOT registered sources.\n# Copied verbatim from agent_reports/run3-{x}.md; each block notes whether it parses as YAML.\n')
        for j,(hd,b,ok,n) in enumerate(blocks,1):
            f.write(f'\n---\n# ---- block {j} · section: {hd} · parses: {"yes" if ok else "NO"} · entries: {n}\n{b}')
    summary.append((x,len(blocks),sum(1 for b in blocks if b[2]),sum(b[3] for b in blocks)))
print('yaml blocks per agent (agent, blocks, parsing, entries):',summary)
