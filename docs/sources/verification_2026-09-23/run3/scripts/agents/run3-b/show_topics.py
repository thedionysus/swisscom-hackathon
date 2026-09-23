import json,sys
SP="<scratchpad>"
s=json.load(open(SP+"/stage0/sitemap_topic_candidates.json"))
full=set(sys.argv[2].split(",")) if len(sys.argv)>2 else set()
for c in sys.argv[1].split(","):
    print("=========",c, {t:v["count"] for t,v in s[c].items()})
    if c in full:
        for t,v in s[c].items():
            if v["count"]:
                print("--",t,v["count"])
                for u in v["shortest"]:
                    print("   ",u)
sm=json.load(open(SP+"/stage0/sitemaps_summary.json"))
for c in sys.argv[1].split(","):
    for h in sm["hosts"][c]:
        print(c,h,json.dumps(sm["result"].get(h),ensure_ascii=False)[:300])
