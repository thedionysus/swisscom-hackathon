#!/usr/bin/env python3
"""Test eSHAB/amtsblattportal bulk export filters per canton and tenant."""
import re
import subprocess
import time

UA = "Mozilla/5.0 swiss-grounding-check"


def get(url):
    r = subprocess.run(["curl", "-g", "-sL", "-m", "45", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    time.sleep(0.6)
    return code, body


def summary(url):
    code, body = get(url)
    total = re.search(r"<total>(\d+)</total>", body)
    tenants = re.findall(r"<primaryTenantCode>([^<]+)</primaryTenantCode>", body)
    cantons = re.findall(r"<cantons>([^<]+)</cantons>", body)
    rubrics = re.findall(r"<rubric>([^<]+)</rubric>", body)
    titles = re.findall(r"<de>([^<]+)</de>", body)
    dates = re.findall(r"<publicationDate>([^<]+)</publicationDate>", body)
    print(code, total.group(1) if total else "-", "| tenants", sorted(set(tenants)), "| cantons", sorted(set(cantons)),
          "| rubrics", sorted(set(rubrics)), "| dates", dates[:3], "|", titles[:3], "|", url)
    return body


B = "https://amtsblattportal.ch/api/v1/publications/xml?publicationStates=PUBLISHED&pageRequest.page=0&pageRequest.size=3"
summary(B)
for c in ["SO", "ZH", "BE", "BS", "BL", "AG"]:
    summary(B + "&cantons=" + c)
for t in ["kabso", "kabzh", "kabbe", "kabbs", "kabbl", "kabag"]:
    summary(B + "&tenant=" + t)
