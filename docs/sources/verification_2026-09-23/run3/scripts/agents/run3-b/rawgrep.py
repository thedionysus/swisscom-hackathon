import sys,os,re,html,hashlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from probe import fetch
rx=sys.argv[1]; w=int(sys.argv[2])
for u in sys.argv[3:]:
    code,ct,size,final,body,fn=fetch(u)
    raw=html.unescape(body.decode("utf-8","ignore"))
    ms=list(re.finditer(rx,raw,re.I))
    print(f"== {u} {code} matches={len(ms)}")
    for m in ms[:4]:
        print("   ~ "+re.sub(r"\s+"," ",raw[max(0,m.start()-w):m.end()+w]))
