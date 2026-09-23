import json,re
SP="<scratchpad>"
keys=["lu.ch","ur.ch","sz.ch","ow.ch","nw.ch","gl.ch","zg.ch","gerichte-zg"]
for f in ["courts_s1_probe.json","guidance_s3a_probe.json","s3b_s4_probe.json"]:
    d=json.load(open(SP+"/"+f))
    items = d.items() if isinstance(d,dict) else [(x.get("url"),x) for x in d]
    print("#####",f)
    for k,v in items:
        if any(x in (k or "") for x in keys):
            fin=v.get("final") or ""
            print(f"  {v.get('code')} {k}" + (f" -> {fin}" if fin and fin.rstrip('/')!=(k or '').rstrip('/') else "") + f" | '{(v.get('title') or '')[:55]}' | {v.get('class') or v.get('err') or ''}")
txt=open(SP+"/guidance_s3a_rows.py").read()
for c in ["OW","NW"]:
    print(c, re.findall(r"\('%s','[a-z]+','[^']+'\)"%c, txt))
