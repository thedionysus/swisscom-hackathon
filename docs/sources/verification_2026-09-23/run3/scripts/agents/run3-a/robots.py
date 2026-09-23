#!/usr/bin/env python3
"""Fetch robots.txt for hosts and print status, Crawl-delay, Sitemap and Disallow counts."""
import re
import subprocess
import sys
import time

UA = "Mozilla/5.0 swiss-grounding-check"
for host in sys.argv[1:]:
    url = f"https://{host}/robots.txt"
    r = subprocess.run(["curl", "-sL", "-m", "30", "-A", UA, "-w", "\n%{http_code}", url], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    delay = sorted(set(re.findall(r"(?im)^crawl-delay:\s*(\S+)", body)))
    sm = re.findall(r"(?im)^sitemap:\s*(\S+)", body)
    dis = re.findall(r"(?im)^disallow:\s*(\S*)", body)
    print(f"{host} | {code} | {len(body)}B | crawl-delay={delay} | sitemaps={sm[:3]} | disallow={len(dis)} {dis[:4]}")
    time.sleep(1)
