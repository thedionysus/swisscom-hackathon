import json,subprocess,collections
D="<scratchpad>/run3-b"
UA="Mozilla/5.0 swiss-grounding-check"
rub=json.load(open(D+"/pages/zg_rubrics.json"))
by=collections.defaultdict(list)
for r in rub: by[r.get("tenantId")].append((r["code"],r["name"]["de"]))
doms={"kabzg":"amtsblatt.zg.ch","kabsz":"amtsblatt.sz.ch","kabnw":"amtsblatt.nw.ch","kabow":"amtsblatt.ow.ch"}
for t,dom in doms.items():
    codes=[c for c,_ in by[t]]
    print("=====",t,dom,"rubrics:",by[t])
    url=f"https://{dom}/api/v1/publications?publicationStates=PUBLISHED&tenant={t}&rubrics={','.join(codes)}&pageRequest.page=0&pageRequest.size=3"
    r=subprocess.run(["curl","-s","--compressed","-A",UA,"-H","Accept: application/json","-w","\n%{http_code}",url],capture_output=True,text=True)
    body,code=r.stdout.rsplit("\n",1)
    print("  ",code,url[:160])
    try:
        d=json.loads(body)
    except Exception:
        print("  ",body[:200]); continue
    print("   total:",d.get("total"))
    for it in d.get("content",[])[:3]:
        m=it["meta"]
        print("   -",m["id"],m["publicationNumber"],m["primaryTenantCode"],m["publicationDate"][:10],m["rubric"],"|",(m["title"].get("de") or "")[:90],"| office:",(m.get("registrationOffice") or {}).get("displayName"),"bfs",(m.get("registrationOffice") or {}).get("municipalityId"))
print("tenants with rubrics:",{k:len(v) for k,v in by.items() if k and k.startswith("kab")})
