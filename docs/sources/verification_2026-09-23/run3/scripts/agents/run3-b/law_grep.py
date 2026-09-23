import json,re
SP="<scratchpad>/stage0/"
rx=re.compile(r"Hund|Tier|Veterinär|Schlicht|Vermittl|Friedensr|Schulferien|Ferien|Volksschul|Gerichtskost|Kosten.*(Gericht|Rechtspflege|Zivil)|Gebühren.*(Gericht|Justiz)",re.I)
for c in ["UR","GL","ZG","OW","NW"]:
    d=json.load(open(SP+f"laws_{c}.json"))
    items=d.get("items") if isinstance(d,dict) else d
    host=d.get("host") if isinstance(d,dict) else None
    print("=====",c,host,"items:",len(items), "keys:", list(items[0].keys())[:8])
    for it in items:
        t=it.get("title") or ""
        if rx.search(t):
            print("   ",it.get("systematic_number"),"|",t[:110],"| abrogated" if it.get("abrogated") else "")
