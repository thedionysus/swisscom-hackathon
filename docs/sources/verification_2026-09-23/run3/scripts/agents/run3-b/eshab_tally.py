import json,subprocess,sys,collections
UA="Mozilla/5.0 swiss-grounding-check"
url=sys.argv[1]
r=subprocess.run(["curl","-s","--compressed","-A",UA,"-H","Accept: application/json",url],capture_output=True,text=True)
d=json.loads(r.stdout)
print("total",d.get("total"))
c=collections.Counter((it["meta"]["primaryTenantCode"],it["meta"]["rubric"]) for it in d["content"])
for k,v in c.most_common(): print("  ",k,v)
for it in d["content"]:
    m=it["meta"]
    if m["primaryTenantCode"]!="shab":
        print("   -",m["publicationNumber"],m["primaryTenantCode"],m["publicationDate"][:10],m["rubric"],m["subRubric"],"|",(m["title"].get("de") or "")[:100],"| office:",(m.get("registrationOffice") or {}).get("displayName"),"bfs",(m.get("registrationOffice") or {}).get("municipalityId"))
        break
