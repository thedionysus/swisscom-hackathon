import json,subprocess,sys
UA="Mozilla/5.0 swiss-grounding-check"
def get(u):
    r=subprocess.run(["curl","-s","-g","--compressed","-A",UA,"-H","Accept: application/json","-w","\n%{http_code}",u],capture_output=True,text=True)
    b,c=r.stdout.rsplit("\n",1); return c,b
c,b=get("https://wissen-backend.webcloud7.ch/steuerbuch")
d=json.loads(b)
print("root",c,"| @type:",d.get("@type"),"| title:",d.get("title"),"| modified:",d.get("modified"),"| items:",len(d.get("items",[])), "| keys:",list(d.keys())[:20])
for it in d.get("items",[])[:3]: print("  -",it.get("@id"),"|",it.get("title"),"|",it.get("@type"))
c,b=get("https://wissen-backend.webcloud7.ch/steuerbuch/@search?b_size=1&metadata_fields=modified")
s=json.loads(b); print("@search",c,"items_total:",s.get("items_total"), "| first:",json.dumps(s.get("items",[])[:1],ensure_ascii=False)[:250])
c,b=get("https://wissen-backend.webcloud7.ch/steuerbuch/@search?b_size=1&portal_type=Document")
s=json.loads(b); print("@search Document",c,"items_total:",s.get("items_total"))
