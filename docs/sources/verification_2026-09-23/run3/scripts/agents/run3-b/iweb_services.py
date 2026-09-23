import sys,os,re,json,html
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from probe import fetch, analyse
url=sys.argv[1]; rx=re.compile(sys.argv[2],re.I)
code,ct,size,final,body,fn=fetch(url)
title,links,words,txt,raw=analyse(body)
print(f"== {url} {code} {size}B '{title}'")
for t in re.findall(r'data-entities="([^"]*)"',raw):
    d=json.loads(html.unescape(t)); rows=d.get("data") if isinstance(d,dict) else d
    print("  rows:",len(rows),"keys:",[k for k in rows[0].keys() if not k.endswith("-sort")] if rows else None)
    hits=0
    for r in rows:
        s=json.dumps(r,ensure_ascii=False)
        name=re.sub(r"<[^>]+>","",html.unescape(str(r.get("name") or r.get("dienstName") or r.get("title") or "")))
        if rx.search(name) or rx.search(re.sub(r"<[^>]+>"," ",html.unescape(s))):
            hrefs=sorted(set(re.findall(r'href=\\"([^"\\]+)',s)))
            print("   -",name[:80],"|",", ".join(hrefs[:3]), "|", {k:re.sub(r"<[^>]+>","",html.unescape(str(v)))[:40] for k,v in r.items() if not k.endswith("-sort") and k not in ("name","dienstName") and v})
            hits+=1
            if hits>=40: break
