"""Parse i-web data-entities table. usage: iweb.py FILE [REGEX]"""
import sys, re, json, html
s=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
rx=re.compile(sys.argv[2],re.I) if len(sys.argv)>2 else None
for m in re.finditer(r'data-entities="([^"]*)"',s):
    raw=html.unescape(m.group(1))
    try: d=json.loads(raw)
    except Exception as e: print('json fail',e,raw[:200]); continue
    rows=d.get('data') if isinstance(d,dict) else d
    print('table keys:',list(d.keys()) if isinstance(d,dict) else 'list','| rows:',len(rows))
    print('row keys/types:',{k:type(v).__name__ for k,v in rows[0].items()})
    print('row0:',json.dumps(rows[0],ensure_ascii=False)[:600])
    def txt(v): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html.unescape(str(v)))).strip()
    if rx:
        hits=[r for r in rows if rx.search(json.dumps(r,ensure_ascii=False))]
        print('matches',len(hits))
        for r in hits[:25]:
            print('  -',' | '.join(txt(v)[:90] for k,v in r.items() if not k.startswith('_') and txt(v))[:300])
