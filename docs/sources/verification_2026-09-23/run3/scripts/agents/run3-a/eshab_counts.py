#!/usr/bin/env python3
"""Count each canton's own gazette notices on amtsblattportal.ch (eSHAB).

For each tenant: fetch /api/v1/tenants/<t>/archive-rubrics, keep the canton's own rubric codes
(suffix -<XX>), then compare three totals from the public bulk XML export (pageRequest.size=1):
  A = cantons=<XX>                              (includes federal SHAB notices)
  B = tenant=<t>                                (tenant filter only)
  C = tenant=<t> + rubrics=<own codes>          (the canton's own gazette)
Also checks OR-semantics of repeated rubrics params: sum of single-rubric totals vs combined.
"""
import json
import re
import subprocess
import time
from urllib.parse import urlencode

UA = "Mozilla/5.0 swiss-grounding-check"
API = "https://amtsblattportal.ch/api/v1"


def get(url, accept=None):
    cmd = ["curl", "-g", "-sL", "-m", "60", "-A", UA, "-w", "\n%{http_code}"]
    if accept:
        cmd += ["-H", "Accept: " + accept]
    r = subprocess.run(cmd + [url], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    time.sleep(0.7)
    return code, body


def total(params):
    q = urlencode(params, doseq=True)
    code, body = get(f"{API}/publications/xml?{q}")
    m = re.search(r"<total>(\d+)</total>", body)
    return (int(m.group(1)) if m else None), code


TENANTS = {"kabso": "SO", "kabzh": "ZH", "kabbe": "BE", "kabbs": "BS", "kabbl": "BL", "kabag": "AG"}
base = {"publicationStates": "PUBLISHED", "pageRequest.page": 0, "pageRequest.size": 1}
_code, _body = get(f"{API}/rubrics", accept="application/json")
ALL = json.loads(_body)
print("rubrics list:", len(ALL), "| tenants:", sorted(set(r.get("tenantId") for r in ALL)))
for t, cc in TENANTS.items():
    own = sorted(r["code"] for r in ALL if r.get("tenantId") == t)
    names = {r["code"]: (r.get("name") or {}).get("de") for r in ALL if r.get("tenantId") == t}
    print(f"== {t} ({cc}) own rubrics by tenantId: {len(own)} {own}")
    print("   names:", names)
    a, ca = total(dict(base, cantons=cc))
    b, cb = total(dict(base, tenant=t))
    print(f"   A cantons={cc}: {a} (HTTP {ca}) | B tenant={t}: {b} (HTTP {cb})")
    if own:
        c, cc_code = total(dict(base, tenant=t, rubrics=own))
        singles = []
        for r in own:
            s, _ = total(dict(base, tenant=t, rubrics=[r]))
            singles.append((r, s))
        ssum = sum(s for _, s in singles if s)
        print(f"   C tenant={t}+own rubrics: {c} (HTTP {cc_code}) | sum of single-rubric totals: {ssum}")
        print("   per rubric:", singles)
