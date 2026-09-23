#!/usr/bin/env python3
"""Gazette follow-up: robots.txt of gazette hosts + Amtsblattportal rubric discovery."""
import json
import re
import subprocess
import time

UA = "Mozilla/5.0 swiss-grounding-check"


def get(url):
    r = subprocess.run(["curl", "-sL", "--max-time", "40", "-A", UA, "-w", "\n%{http_code} %{content_type}", url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    body, _, meta = r.stdout.rpartition("\n")
    return meta, body


print("=== robots.txt of gazette hosts")
for h in ["amtsblattportal.ch", "www.amtsblattportal.ch", "fo.fr.ch", "abl.fr.ch", "www.faovd.ch", "fao.ge.ch",
          "rsju.jura.ch", "www.guichetunique.ch", "www.ne.ch"]:
    meta, body = get(f"https://{h}/robots.txt")
    is_txt = not body.lstrip().lower().startswith("<")
    lines = [ln.strip() for ln in body.splitlines() if re.match(r"(?i)\s*(user-agent|disallow|allow|sitemap|crawl-delay)\s*:", ln)]
    root_block = any(re.match(r"(?i)disallow:\s*/\s*$", ln) for ln in lines)
    print(f"{h}: {meta} {'' if is_txt else '(HTML, no robots.txt)'} | 'Disallow: /' present={root_block} | "
          f"{len(lines)} rule lines | first: {lines[:4]}")
    time.sleep(0.4)

print("=== rubric endpoints")
for path in ["/api/v1/rubrics", "/api/v1/rubrics?tenant=kabfr", "/api/v1/tenants/kabfr/rubrics"]:
    meta, body = get("https://amtsblattportal.ch" + path)
    print(path, meta, len(body), body[:300].replace("\n", " "))
    if body.strip().startswith("[") or body.strip().startswith("{"):
        try:
            d = json.loads(body)
            rows = d if isinstance(d, list) else (d.get("content") or d.get("items") or [])
            print("   rows:", len(rows))
            open("rubrics_" + re.sub(r"\W+", "_", path) + ".json", "w").write(body)
        except Exception as e:  # noqa
            print("   parse error", e)
    time.sleep(0.4)
