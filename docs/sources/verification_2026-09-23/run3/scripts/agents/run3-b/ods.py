import json,subprocess,sys
UA="Mozilla/5.0 swiss-grounding-check"
def get(u):
    r=subprocess.run(["curl","-s","-g","--compressed","-A",UA,"-w","\n%{http_code}",u],capture_output=True,text=True)
    b,c=r.stdout.rsplit("\n",1); return c,b
portal=sys.argv[1]
for ds in sys.argv[2:]:
    c,b=get(f"https://{portal}/api/explore/v2.1/catalog/datasets/{ds}")
    try:
        m=json.loads(b); meta=m.get("metas",{}).get("default",{})
        print("==",ds,c,"| title:",meta.get("title"),"| modified:",meta.get("modified"),"| records:",meta.get("records_count"),"| publisher:",meta.get("publisher"),"| license:",meta.get("license"))
        print("   fields:",[(f["name"],f["type"]) for f in m.get("fields",[])])
    except Exception as e:
        print("==",ds,c,"meta err",b[:200])
    c,b=get(f"https://{portal}/api/explore/v2.1/catalog/datasets/{ds}/records?limit=3")
    try:
        d=json.loads(b); print("   records total_count:",d.get("total_count"))
        for r in d.get("results",[])[:3]: print("   -",json.dumps(r,ensure_ascii=False)[:300])
    except Exception: print("   records err",c,b[:200])
