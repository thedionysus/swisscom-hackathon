import json,subprocess,re,urllib.parse
D="<scratchpad>/run3-b/pages/"
UA="Mozilla/5.0 swiss-grounding-check"
def get(u):
    r=subprocess.run(["curl","-s","-g","--compressed","-A",UA,"-H","Accept: application/json","-w","\n%{http_code}",u],capture_output=True,text=True)
    b,c=r.stdout.rsplit("\n",1); return c,b
tree=json.load(open(D+"lexfind_sz_tree.json"))
ids=[k for k in tree if k]
tols=[]
for i in range(0,len(ids),90):
    q="&".join("tols_for_systematics[]="+x for x in ids[i:i+90])
    c,b=get("https://www.lexfind.ch/api/fe/de/entities/19/systematics?active_only=true&"+q)
    d=json.loads(b)
    for k,v in d.items():
        for t in (v.get("tols") or []):
            tols.append((v.get("identifier"),t))
    print("batch",i,c,len(b))
print("texts:",len(tols))
print("sample tol keys:",json.dumps(tols[0][1],ensure_ascii=False)[:500])
rx=re.compile(r"Hund|Tier|Veterinär|Schlicht|Vermittl|Gerichtsorg|Justiz|Kosten|Gebühr|Steuergesetz|Steuerverordnung|Strassenverkehr|Motorfahrzeug|Volksschul|Schulferien|Ferien|Amtsblatt",re.I)
for ident,t in tols:
    title=t.get("title") or ""
    if rx.search(title):
        print("  ",t.get("systematic_number"),"|",title[:100],"|",t.get("id"))
json.dump(tols,open(D+"lexfind_sz_tols.json","w"))
