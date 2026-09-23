import sys,os,re,html,hashlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from probe import fetch
rx=re.compile(sys.argv[1],re.I)
for u in sys.argv[2:]:
    code,ct,size,final,body,fn=fetch(u)
    raw=body.decode("utf-8","ignore")
    seen=[]
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',raw,re.I|re.S):
        h=m.group(1); a=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",m.group(2)))).strip()
        if rx.search(h+" "+a) and (h,a) not in seen: seen.append((h,a))
    for t in re.findall(r'data-entities="([^"]*)"',raw):
        for h,a in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>',html.unescape(t).replace('\\/','/').replace('\\"','"')):
            a=re.sub(r"<[^>]+>","",a).strip()
            if rx.search(h+" "+a) and (h,a) not in seen: seen.append((h,a+" [table]"))
    print(f"== {u} {code}: {len(seen)}")
    for h,a in seen[:25]: print(f"    -> {h} [{a[:90]}]")
