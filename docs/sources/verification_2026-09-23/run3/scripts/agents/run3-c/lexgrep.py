"""usage: lexgrep.py HOST NR REGEX [max] -- grep the full LexWork JSON (meta + show_as_json) text for REGEX"""
import sys, subprocess, re, html, json
host,nr,rx=sys.argv[1],sys.argv[2],sys.argv[3]; mx=int(sys.argv[4]) if len(sys.argv)>4 else 3
pat=re.compile(rx,re.I)
for suffix in ['', '/show_as_json']:
    u=f'https://{host}/api/de/texts_of_law/{nr}{suffix}'
    r=subprocess.run(['curl','-sL','--max-time','60','-A','Mozilla/5.0 swiss-grounding-check',u],capture_output=True,text=True)
    b=r.stdout
    try: b=json.dumps(json.loads(b),ensure_ascii=False)
    except Exception: pass
    t=re.sub(r'\\[nrt]',' ',b)
    t=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))
    hits=list(pat.finditer(t))
    print(u,'chars',len(t),'hits',len(hits))
    for m in hits[:mx]: print('   >>',t[max(0,m.start()-150):m.end()+120])
