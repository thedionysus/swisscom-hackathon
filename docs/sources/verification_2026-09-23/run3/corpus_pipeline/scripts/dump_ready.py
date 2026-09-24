import os, yaml, json, collections
R = "<scratchpad>/wt-run3/docs/sources/verification_2026-09-23/run3/ready_sources"
keys = collections.Counter(); fc_keys = collections.defaultdict(collections.Counter)
for f in sorted(os.listdir(R)):
    text = open(os.path.join(R, f), encoding="utf-8").read()
    d = yaml.safe_load(text)
    comments = [l for l in text.splitlines() if l.startswith("#")]
    for k in d: keys[k] += 1
    for k in (d.get("fetch_config") or {}): fc_keys[d["fetch_strategy"]][k] += 1
    fc = d.get("fetch_config") or {}
    print(f"== {d['id']} [{d['fetch_strategy']}] {d['base_url']} extent={d['default_extent_id']} auth={d['authority']} cats={d.get('categories')} narrow={d.get('allow_narrowing')} lic={d.get('license')}")
    print("   name:", d["name"])
    for c in comments: print("   ", c[:220])
    print("   fc:", json.dumps(fc, ensure_ascii=False)[:600])
print(keys)
for s, c in fc_keys.items(): print(s, dict(c))
