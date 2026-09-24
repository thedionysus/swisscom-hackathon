import os, re, yaml
from urllib.parse import urlparse, unquote
R = "<scratchpad>/wt-run3/docs/sources/verification_2026-09-23/run3"
reports = {f: open(f"{R}/agent_reports/{f}", encoding="utf-8").read().splitlines()
           for f in ["run3-a.md", "run3-b.md", "run3-c.md", "run3-d.md", "run3-e.md"]}
for f in sorted(os.listdir(f"{R}/ready_sources")):
    d = yaml.safe_load(open(f"{R}/ready_sources/{f}", encoding="utf-8"))
    if d["fetch_strategy"] != "pdf":
        continue
    print(f"##### {d['id']}")
    for url in d["fetch_config"]["urls"]:
        p = urlparse(url)
        key = unquote(p.path.rstrip("/").split("/")[-1]) if not re.search(r"/_doc/|/document/|/law/|/get/file/", p.path) else p.path
        key = key.split("?")[0]
        print(f"  URL {url}\n   key={key}")
        hits = 0
        for rep, lines in reports.items():
            for n, line in enumerate(lines, 1):
                if key and (key in line or key in unquote(line)):
                    i = line.find(key) if key in line else unquote(line).find(key)
                    print(f"   {rep}:{n}: {line[max(0,i-350):i+150]}")
                    hits += 1
                    if hits > 4: break
            if hits > 4: break
