"""LexWork check. usage: lexwork.py HOST NR [REGEX]  -> meta from /api/de/texts_of_law/NR, then grep show_as_json text"""
import sys, subprocess, json, re, html
host,nr=sys.argv[1],sys.argv[2]; pat=re.compile(sys.argv[3],re.I) if len(sys.argv)>3 else None
def get(u):
    r=subprocess.run(['curl','-sL','--max-time','60','-A','Mozilla/5.0 swiss-grounding-check','-w','\n%{http_code}',u],capture_output=True,text=True)
    body,code=r.stdout.rsplit('\n',1); return code,body
code,b=get(f'https://{host}/api/de/texts_of_law/{nr}')
print('meta',code,len(b))
try:
    d=json.loads(b); tol=d.get('text_of_law',d)
    for k in ['systematic_number','title','abbreviation','enactment','is_active','canonical_link','version_active_since','dta_url']:
        if k in tol: print('  ',k,'=',str(tol[k])[:150])
    if 'canonical_link' not in tol: print('   keys:',list(tol.keys())[:30])
except Exception as e: print('  not json',e,b[:200])
code,b=get(f'https://{host}/api/de/texts_of_law/{nr}/show_as_json')
print('show_as_json',code,len(b))
if pat:
    t=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',b)))
    k=0
    for m in pat.finditer(t):
        print('   >>',t[max(0,m.start()-160):m.end()+140]); k+=1
        if k>=3: break
    if not k: print('   >> (no match)')
