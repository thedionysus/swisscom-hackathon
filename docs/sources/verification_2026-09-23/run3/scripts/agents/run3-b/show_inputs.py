import json,sys
SP="<scratchpad>"
d=json.load(open(SP+"/stage0/law_hits.json"))
for c in sys.argv[1:]:
    v=d.get(c)
    print("=====",c)
    if not v:
        print("  (no entry)"); continue
    for topic,items in v.items():
        print(" --",topic, len(items))
        for it in items:
            print("    ",it.get("nr"),"|",it.get("title")[:120],"|",it.get("api"))
