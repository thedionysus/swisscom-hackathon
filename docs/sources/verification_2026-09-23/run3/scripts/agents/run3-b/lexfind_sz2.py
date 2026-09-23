import json,subprocess
D="<scratchpad>/run3-b/pages/"
UA="Mozilla/5.0 swiss-grounding-check"
def get(u):
    r=subprocess.run(["curl","-s","-g","--compressed","-A",UA,"-H","Accept: application/json","-w","\n%{http_code}",u],capture_output=True,text=True)
    b,c=r.stdout.rsplit("\n",1); return c,b
c,b=get("https://www.lexfind.ch/api/fe/de/entities/19/systematics?active_only=true")
open(D+"lexfind_sz_tree.json","w").write(b)
d=json.loads(b)
print(c, type(d), (list(d.keys()) if isinstance(d,dict) else len(d)))
def walk(n,depth=0,out=[]):
    if isinstance(n,dict):
        out.append((depth,n.get("id"),n.get("systematic_number") or n.get("number"),n.get("title") or n.get("name")))
        for k in ("children","nodes","systematics"):
            for ch in n.get(k) or []: walk(ch,depth+1,out)
    elif isinstance(n,list):
        for ch in n: walk(ch,depth,out)
    return out
root=d.get("systematics") if isinstance(d,dict) and "systematics" in d else d
print(json.dumps(root if not isinstance(root,list) else root[0],ensure_ascii=False)[:600])
