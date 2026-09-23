import sys,os,re,html,urllib.parse
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from probe import fetch, analyse
base=sys.argv[1]  # e.g. https://www.ur.ch/suchen?query=
for q in sys.argv[2:]:
    u=base+urllib.parse.quote(q)
    code,ct,size,final,body,fn=fetch(u)
    title,links,words,txt,raw=analyse(body)
    print(f"== [{q}] {code} {size}B words={words} {u}")
    res=[]
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',raw,re.I|re.S):
        h=m.group(1); a=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",m.group(2)))).strip()
        if re.search(r"_rte/|_doc/|dienstleistungen/|/\d{3,}$|\.pdf",h) and (h,a) not in res: res.append((h,a))
    for h,a in res[:12]: print(f"    -> {h} [{a[:80]}]")
    i=txt.find("Ergebnis"); 
    if i>=0: print("    txt:",txt[i:i+200])
