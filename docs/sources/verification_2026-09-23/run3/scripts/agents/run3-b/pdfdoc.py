import sys,os,re,io
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from probe import fetch
from pypdf import PdfReader
u=sys.argv[1]; rx=re.compile(sys.argv[2],re.I) if len(sys.argv)>2 else None
code,ct,size,final,body,fn=fetch(u)
print(code,ct,size,final)
if body[:5]==b"%PDF-":
    r=PdfReader(io.BytesIO(body)); n=len(r.pages)
    t=" ".join((r.pages[i].extract_text() or "") for i in range(min(n,40)))
    t=re.sub(r"\s+"," ",t)
    print("pages",n,"chars(first40)",len(t))
    print("head:",t[:400])
    if rx:
        for m in list(rx.finditer(t))[:5]: print("  ~",t[max(0,m.start()-80):m.end()+150])
