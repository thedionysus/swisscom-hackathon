#!/usr/bin/env python3
"""Print the stage-0 inputs for group run3-a (local files only, no network)."""
import json

SP = "<scratchpad>"
CANTONS = ["ZH", "BE", "BS", "BL", "SO", "AG"]

lh = json.load(open(SP + "/stage0/law_hits.json"))
print("#### LAW HITS")
for c in CANTONS:
    print("=====", c)
    for topic, hits in lh.get(c, {}).items():
        print("  --", topic, len(hits))
        for h in hits:
            print("      ", h.get("nr"), "|", h.get("title", "")[:120], "|", h.get("api"))

print("\n#### OPENCASELAW")
oc = json.load(open(SP + "/opencaselaw_courts_2026-09-23.json"))
for c in CANTONS:
    rows = [r for r in oc if r.get("canton") == c]
    tot = sum(r["decision_count"] for r in rows)
    print("=====", c, "courts", len(rows), "decisions", tot)
    for r in sorted(rows, key=lambda r: -r["decision_count"]):
        stale = "STALE" if (r.get("latest") or "0") < "2026-01-01" else ""
        print("   ", r["court"], r["decision_count"], r["earliest"], r["latest"], stale, "sparse" if r.get("sparse") else "")

print("\n#### TOPIC COUNTS")
tc = json.load(open(SP + "/stage0/sitemap_topic_candidates.json"))
for c in CANTONS:
    print("=====", c, {t: v.get("count") for t, v in tc.get(c, {}).items()})

print("\n#### SITEMAP SUMMARY")
ss = json.load(open(SP + "/stage0/sitemaps_summary.json"))
for c in CANTONS:
    for h in ss["hosts"].get(c, []):
        v = ss["result"].get(h, {})
        print(c, h, v.get("urls"), v.get("delay"), v.get("log"))
