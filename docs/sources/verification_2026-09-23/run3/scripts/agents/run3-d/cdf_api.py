#!/usr/bin/env python3
"""Try the La Chaux-de-Fonds WCF JSON API used by the client bundle."""
import json
import re
import subprocess
import time

UA = "Mozilla/5.0 swiss-grounding-check"


def post(path, payload):
    r = subprocess.run(["curl", "-s", "--max-time", "40", "-A", UA, "-X", "POST",
                        "-H", "Content-Type: application/json; charset=utf-8",
                        "-H", "Referer: https://www.chaux-de-fonds.ch/rapports-et-reglements/reglementation",
                        "--data", json.dumps(payload), "-w", "\n%{http_code} %{content_type} %{size_download}",
                        "https://www.chaux-de-fonds.ch" + path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    body, _, meta = r.stdout.rpartition("\n")
    return meta, body


for page in ["/rapports-et-reglements/reglementation", "rapports-et-reglements/reglementation",
             "https://www.chaux-de-fonds.ch/rapports-et-reglements/reglementation"]:
    meta, body = post("/Api/Page.svc/detail", {"page": page})
    print("detail", repr(page), meta, body[:300].replace("\n", " "))
    if body.strip().startswith("{") or body.strip().startswith("["):
        open("cdf_detail.json", "w").write(body)
        pdfs = sorted(set(re.findall(r'[^"\\]*\.pdf', body)))
        print("   pdf refs:", len(pdfs), pdfs[:5])
        lists = sorted(set(re.findall(r'"[^"]*(?:Lists|Documents|liste)[^"]*"', body)))[:10]
        print("   list refs:", lists)
        break
    time.sleep(0.5)
