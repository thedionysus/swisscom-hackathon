import json,subprocess,sys
UA="Mozilla/5.0 swiss-grounding-check"
def get(url):
    r=subprocess.run(["curl","-s","--compressed","-A",UA,"-H","Accept: application/json","-w","\n%{http_code}",url],capture_output=True,text=True)
    body,code=r.stdout.rsplit("\n",1)
    return code,body
for url in sys.argv[1:]:
    code,body=get(url)
    print("==",url,"->",code,len(body),"B")
    try:
        d=json.loads(body)
    except Exception:
        print(body[:300]); continue
    if isinstance(d,dict):
        print("   top keys:",[k for k in d.keys()])
        for k in d:
            if k!="content": print("   ",k,"=",json.dumps(d[k])[:200])
        for it in (d.get("content") or [])[:3]:
            m=it["meta"]
            print("   -",m["publicationNumber"],m["primaryTenantCode"],m["cantons"],m["publicationDate"][:10],m["rubric"],m["subRubric"],"|",(m["title"].get("de") or "")[:90],"| office:",(m.get("registrationOffice") or {}).get("displayName"),"bfs",(m.get("registrationOffice") or {}).get("municipalityId"))
