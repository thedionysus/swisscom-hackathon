#!/usr/bin/env python3
"""Count Amtsblattportal publications per tenant (external flag check)."""
import json
import subprocess
import time

UA = "Mozilla/5.0 swiss-grounding-check"
for tenant in ["kabfr", "kabvd", "kabne", "kabge", "kabju", "kabzh"]:
    url = ("https://amtsblattportal.ch/api/v1/publications?publicationStates=PUBLISHED"
           f"&tenants={tenant}&pageRequest.page=0&pageRequest.size=1")
    r = subprocess.run(["curl", "-s", "--max-time", "60", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    try:
        d = json.loads(body)
        total = d.get("total", d.get("totalElements", (d.get("pageRequest") or {}).get("total")))
        keys = list(d.keys())
        first = (d.get("content") or d.get("items") or [None])[0]
        print(tenant, code, "keys", keys, "total", total,
              "| first:", json.dumps(first, ensure_ascii=False)[:200] if first else None)
    except Exception as e:  # noqa
        print(tenant, code, "parse error", e, body[:200])
    time.sleep(0.5)
