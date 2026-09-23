import json
D="<scratchpad>/run3-b"
d=json.load(open(D+"/pages/eshab_tenants.json"))
print("tenants:",len(d))
print("keys:",sorted(d[0].keys()))
for t in sorted(d,key=lambda x:(x.get("type") or "",x.get("canton") or "")):
    dom=[k for k in t.keys() if "omain" in k]
    print(t.get("type"),t.get("canton"),t["id"],"external=",t.get("external"),"|",(t.get("title") or {}).get("de"),"|",{k:t.get(k) for k in dom})
