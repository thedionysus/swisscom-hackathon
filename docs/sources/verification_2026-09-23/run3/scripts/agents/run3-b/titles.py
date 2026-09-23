import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from probe import fetch, analyse
for u in sys.argv[1:]:
    code,ct,size,final,body,fn=fetch(u)
    title,links,words,txt,raw=analyse(body)
    print(f"{code} {u} -> '{title}' words={words}" + ("" if final.rstrip('/')==u.rstrip('/') else f" final={final}"))
