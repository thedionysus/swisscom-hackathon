"""Convert Run 3 sources into new-pipeline manifest entries, check them offline, validate with load_manifest.

Run: PYTHONPATH=<wt-main>/src <venv python> convert_run3.py
No network. Reads: Run 3 folder, wt-main manifest + code, the agents' saved pages (saved_index.json).
Writes (newpipe/): run3_manifest_candidates.yaml, run3_compatibility.csv, conversion_report.json
"""
import csv
import json
import os
import re
import sys
from collections import OrderedDict

import yaml

from run3_decisions import DECLARED_CANTONS, DECLARED_COMMUNES, HTML, NEW
from swiss_grounding.corpus.connectors.html_meta import page_meta
from swiss_grounding.corpus.connectors.html_page import parse_crawled_page
from swiss_grounding.corpus.manifest import Manifest, SourceEntry, load_manifest
from swiss_grounding.corpus.models import SourceSpec
from swiss_grounding.locations.seed import seed_locations

S = "<scratchpad>"
R3 = S + "/newpipe/run3_copy/docs/sources/verification_2026-09-23/run3"  # git archive of c93ae3f; wt-run3 was removed mid-session
WT = S + "/wt-main"
OUT = S + "/newpipe"
DECLARED_PATH = WT + "/manifests/declared-scope.yaml"

catalogue = list(csv.DictReader(open(R3 + "/source_catalogue.csv", encoding="utf-8")))
ready = {f[:-5]: yaml.safe_load(open(os.path.join(R3, "ready_sources", f), encoding="utf-8"))
         for f in sorted(os.listdir(R3 + "/ready_sources")) if f.endswith(".yaml")}
declared = yaml.safe_load(open(DECLARED_PATH, encoding="utf-8"))
saved_index = json.load(open(OUT + "/saved_index.json"))
locations = {loc.id for loc in seed_locations()}


def absu(base, path):
    return path if path.startswith(("http://", "https://")) else base.rstrip("/") + path


def dedupe_prefixes(prefixes):
    """Drop a prefix another prefix of the same source already covers (html.py:186-188 is str.startswith)."""
    unique = list(OrderedDict.fromkeys(prefixes))
    return [p for p in unique if not any(q != p and p.startswith(q) for q in unique)]


def new_id(run3_id):
    return run3_id.replace("-", "_")


def level_of(extent):
    return "municipal" if extent.count("-") == 2 else "cantonal"


def tier_of(extent, override=None):
    if override:
        return override
    return 1 if extent in DECLARED_CANTONS or extent in DECLARED_COMMUNES else 2


# ---------------------------------------------------------------- overlap with declared-scope.yaml
declared_prefixes = {s["id"]: tuple((s.get("config") or {}).get("allow_prefixes") or ()) +
                     tuple((s.get("config") or {}).get("pdf_allow_prefixes") or ()) for s in declared["sources"]}


def run3_urls(row):
    urls = []
    y = ready.get(row["id"])
    if y:
        fc = y.get("fetch_config") or {}
        urls += [absu(y["base_url"], p) for p in fc.get("start_paths", [])]
        urls += [absu(y["base_url"], p) for p in fc.get("path_allowlist", [])]
        urls += list(fc.get("urls", []))
        if fc.get("url"):
            urls.append(fc["url"])
    urls += re.findall(r"https?://[^\s;]+", row.get("entry_points") or "")
    return [u for u in urls if u]


def overlaps(url):
    hits = []
    for sid, prefixes in declared_prefixes.items():
        for p in prefixes:
            if url.startswith(p) or p.startswith(url):
                hits.append((sid, p))
    return hits


overlap_report = {}
for row in catalogue:
    found = OrderedDict()
    for u in run3_urls(row):
        for sid, p in overlaps(u):
            found.setdefault(sid, set()).add(p)
    if found:
        overlap_report[row["id"]] = {sid: sorted(ps) for sid, ps in found.items()}

# ---------------------------------------------------------------- build entries
entries = []           # (section, entry dict, comment lines, meta)
row_manifest = {}      # run3 row id -> manifest id
fold_targets = {"ai_ferienplan": "ai_guidance", "sg_gerichte_kostenmerkblatt": "sg_gerichte_info",
                "zg-pdfs": "zg_hunde_ferien", "ju-court-tariff": "ju_justice"}

for rid, y in ready.items():
    if y["fetch_strategy"] != "html_crawl" or rid in overlap_report:
        continue
    d = HTML[rid]
    fc = y["fetch_config"]
    base = y["base_url"]
    starts = list(OrderedDict.fromkeys(d.get("first_start", []) + [absu(base, p) for p in fc["start_paths"]]))
    prefixes = dedupe_prefixes([absu(base, p) for p in fc["path_allowlist"]])
    extent = y["default_extent_id"]
    config = OrderedDict(start_urls=starts, allow_prefixes=prefixes)
    for key in ("pdf_allow_prefixes", "pdf_link_patterns", "language_links_selector", "content_selector",
                "sitemap_urls", "sitemap_include", "delay_seconds"):
        if key in d:
            config[key] = d[key]
    config["max_pages"] = d["max_pages"]
    config["max_pdfs"] = d.get("max_pdfs", 0)
    entry = OrderedDict(id=new_id(rid), name=d.get("name") or y["name"], publisher=d["publisher"],
                        authority=y["authority"], level=level_of(extent), extent_id=extent, connector="html",
                        tier=tier_of(extent), languages=[fc.get("language", "de")], config=config)
    comments = [f"Run 3: {rid} (html_crawl, {y['base_url']})"]
    if d.get("lu"):
        comments.append("content_selector #mainContent: NOT from an agent report; found by parsing the agents' saved LU "
                        "pages offline (0 sections without it, 1-15 with it). Review before merging.")
    elif "content_selector" in d:
        comments.append(f"content_selector {d['content_selector']}: content marker documented in the agent report")
    for n in (d.get("note"), d.get("fold_note")):
        if n:
            comments.append(n)
    entries.append((1, entry, comments, {"rows": [rid], "pins": d.get("pins", []), "lu": d.get("lu", False)}))
    row_manifest[rid] = entry["id"]
for rid, target in fold_targets.items():
    row_manifest[rid] = target

for n in NEW:
    extent = n["extent_id"]
    config = OrderedDict(start_urls=n["start_urls"], allow_prefixes=n["allow_prefixes"])
    for key in ("pdf_allow_prefixes", "pdf_link_patterns", "content_selector", "sitemap_urls", "sitemap_include",
                "delay_seconds"):
        if key in n:
            config[key] = n[key]
    config["max_pages"] = n["max_pages"]
    config["max_pdfs"] = n["max_pdfs"]
    entry = OrderedDict(id=n["id"], name=n["name"], publisher=n["publisher"], authority=n["authority"],
                        level=level_of(extent), extent_id=extent, connector="html", tier=tier_of(extent, n.get("tier")),
                        languages=n["languages"], config=config)
    comments = [f"Run 3: {', '.join(n['rows'])}"]
    if n.get("lu"):
        comments.append("content_selector #mainContent: from the offline parse of saved LU pages, not an agent report")
    comments.append(n["note"])
    entries.append((n.get("section", 1), entry, comments,
                    {"rows": n["rows"], "pins": n.get("pins", []), "saved_as": n.get("saved_as", {}),
                     "unverified": n.get("unverified", False), "lu": n.get("lu", False)}))
    for r in n["rows"]:
        row_manifest[r] = n["id"]

entries.sort(key=lambda e: (e[0], e[1]["tier"], e[1]["extent_id"], e[1]["id"]))

# ---------------------------------------------------------------- self-checks (offline)
checks = {}
declared_ids = {s["id"] for s in declared["sources"]}


def saved_html(url, saved_as):
    alias = saved_as.get(url)
    if alias and alias.startswith("FILE:"):
        return open(alias[5:], "rb").read().decode("utf-8", errors="replace")
    key = alias or url
    for k in (key, key.rstrip("/"), key + "/"):
        if k in saved_index:
            return open(saved_index[k], "rb").read().decode("utf-8", errors="replace")
    return None


for section, e, _comments, meta in entries:
    c = e["config"]
    problems = []
    if not re.fullmatch(r"[a-z0-9_]+", e["id"]):
        problems.append("id pattern")
    if e["id"] in declared_ids:
        problems.append("id already declared")
    for u in c["start_urls"]:
        if not any(u.startswith(p) for p in c["allow_prefixes"]):
            problems.append(f"start URL outside allow_prefixes: {u}")
    if e["extent_id"] not in locations:
        problems.append(f"extent {e['extent_id']} not in seed_locations()")
    pdf_prefixes = c.get("pdf_allow_prefixes") or c["allow_prefixes"]
    for pin in meta["pins"]:
        if not any(pin.startswith(p) for p in pdf_prefixes):
            problems.append(f"pinned PDF outside pdf prefixes: {pin}")
    # offline parse of the saved start pages with this entry's own config
    spec = SourceSpec(id=e["id"], name=e["name"], publisher=e["publisher"], authority=e["authority"], level=e["level"],
                      extent_id=e["extent_id"], connector="html", tier=e["tier"], languages=tuple(e["languages"]),
                      config=dict(c))
    patterns = tuple(re.compile(p) for p in c.get("pdf_link_patterns", []))
    parsed, sections, emitted, found_pdfs = 0, 0, 0, []
    for u in c["start_urls"]:
        html = saved_html(u, meta.get("saved_as", {}))
        if html is None:
            continue
        parsed += 1
        page = parse_crawled_page(html, u, spec, patterns)
        sections += len(page.sections)
        emitted += int(page.emit and bool(page.sections))
        found_pdfs += [h for h, _t in page.pdf_links if any(h.startswith(p) for p in pdf_prefixes)]
    pins_found = [pin for pin in meta["pins"] if any(h.startswith(pin) for h in found_pdfs)]
    checks[e["id"]] = dict(section=section, tier=e["tier"], problems=problems, start_urls=len(c["start_urls"]),
                           start_pages_saved=parsed, sections_on_saved_start_pages=sections,
                           start_pages_emitting=emitted, pdfs_in_scope_on_saved_start_pages=len(found_pdfs),
                           pins=len(meta["pins"]), pins_found_offline=len(pins_found), rows=meta["rows"],
                           unverified=meta.get("unverified", False), lu=meta.get("lu", False))


# ---------------------------------------------------------------- emit YAML
def flow(value):
    return json.dumps(value, ensure_ascii=False)


lines = [
    "# Run 3 (2026-09-23) sources converted for the new corpus pipeline (candidates, not merged).",
    "# Generated by newpipe/convert_run3.py from the Run 3 ready_sources/*.yaml and source_catalogue.csv.",
    "# Schema: src/swiss_grounding/corpus/manifest.py (SourceEntry); only the html connector applies (fedlex is law).",
    "# Tiers: 1 = inside ADR 0009's declared scope (ZH, BE, VD, GE, TI, GR and the seven declared communes);",
    "#        2 = other cantons and cities (breadth, ADR 0009 consequence 2); 3 = bulk or gazette collections (opt-in).",
    "# Fixed PDF lists become: crawl only the page that links them + pdf_allow_prefixes pinned to their folder/URL.",
    "version: 1",
    "sources:",
]
current_section = None
for section, e, comments, _meta in entries:
    if section != current_section:
        current_section = section
        lines.append("")
        lines.append("  # ================= SECTION 1: convertible now =================" if section == 1 else
                     "  # ================= SECTION 2: valid config, blocked until a small pipeline change =================")
    lines.append("")
    for cmt in comments:
        lines.append(f"  # {cmt}")
    lines.append(f"  - id: {e['id']}")
    for key in ("name", "publisher"):
        lines.append(f"    {key}: {flow(e[key])}")
    for key in ("authority", "level", "extent_id", "connector", "tier"):
        lines.append(f"    {key}: {e[key]}")
    lines.append(f"    languages: {flow(e['languages'])}")
    lines.append("    config:")
    for k, v in e["config"].items():
        lines.append(f"      {k}: {flow(v)}")
yaml_path = OUT + "/run3_manifest_candidates.yaml"
open(yaml_path, "w", encoding="utf-8").write("\n".join(lines) + "\n")

# ---------------------------------------------------------------- validate with the real loader
validation = {}
try:
    m = load_manifest(yaml_path)
    validation["candidates"] = f"PASS: {len(m.sources)} sources"
except Exception as exc:  # noqa: BLE001
    validation["candidates"] = f"FAIL: {exc}"
per_entry = {"pass": 0, "fail": []}
for _s, e, _c, _m in entries:
    try:
        SourceEntry.model_validate(json.loads(json.dumps(e)))
        per_entry["pass"] += 1
    except Exception as exc:  # noqa: BLE001
        per_entry["fail"].append((e["id"], str(exc)[:300]))
validation["per_entry"] = per_entry
cand = yaml.safe_load(open(yaml_path, encoding="utf-8"))
try:
    merged = Manifest.model_validate({"version": 1, "sources": declared["sources"] + cand["sources"]})
    validation["merged_with_declared"] = f"PASS: {len(merged.sources)} sources ({len(declared['sources'])} declared + {len(cand['sources'])} candidates)"
except Exception as exc:  # noqa: BLE001
    validation["merged_with_declared"] = f"FAIL: {exc}"
# every clash, not only the first the validator reports
clashes = []
all_sources = [(s["id"], tuple(s["config"].get("allow_prefixes") or ()) + tuple(s["config"].get("pdf_allow_prefixes") or ()))
               for s in declared["sources"] + cand["sources"]]
for i, (a_id, a) in enumerate(all_sources):
    for b_id, b in all_sources[i + 1:]:
        for x in a:
            for y2 in b:
                if x.startswith(y2) or y2.startswith(x):
                    clashes.append((a_id, b_id, x, y2))
validation["prefix_clashes_all_pairs"] = clashes
ids = [s["id"] for s in declared["sources"] + cand["sources"]]
validation["duplicate_ids"] = sorted({i for i in ids if ids.count(i) > 1})

json.dump({"validation": validation, "checks": checks, "overlap_with_declared": overlap_report,
           "row_manifest": row_manifest}, open(OUT + "/conversion_report.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(validation, indent=1, ensure_ascii=False))
print("entries:", len(entries), "| sections:", {s: sum(1 for e in entries if e[0] == s) for s in (1, 2)},
      "| tiers:", {t: sum(1 for e in entries if e[1]['tier'] == t) for t in (1, 2, 3)})
bad = {k: v["problems"] for k, v in checks.items() if v["problems"]}
print("self-check problems:", bad or "none")
