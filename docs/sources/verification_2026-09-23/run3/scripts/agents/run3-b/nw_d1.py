import sys,os,re,html
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from probe import fetch
code,ct,size,final,body,fn=fetch("https://www.nw.ch/gemeindenmain")
raw=body.decode("utf-8","ignore")
areas=re.findall(r'<area href="([^"]+)"[^>]*title="([^"]+)"',raw)
print("image-map areas:",len(areas)); print(sorted(set(areas)))
code,ct,size,final,body,fn=fetch("https://www.nw.ch/biddirektionssekrdienste/520")
raw=html.unescape(body.decode("utf-8","ignore"))
for m in re.finditer(r'Ferienplan',raw):
    s=raw[max(0,m.start()-300):m.end()+300]
    hs=re.findall(r'href="([^"]+)"',s)
    if hs: print("near 'Ferienplan':",hs[:4])
