"""Offline dry-parse: every saved page inside each candidate entry's allow_prefixes, parsed with that entry's config."""
import json, re, yaml
from swiss_grounding.corpus.models import SourceSpec
from swiss_grounding.corpus.connectors.html_page import parse_crawled_page
from swiss_grounding.corpus.connectors.html_meta import page_meta
S = "<scratchpad>"
idx = json.load(open(S + "/newpipe/saved_index.json"))
cand = yaml.safe_load(open(S + "/newpipe/run3_manifest_candidates.yaml"))
tot = {"pages": 0, "emitted": 0, "empty": 0, "not_emitted": 0}
out = {}
for e in cand["sources"]:
    c = e["config"]
    spec = SourceSpec(id=e["id"], name=e["name"], publisher=e["publisher"], authority=e["authority"], level=e["level"],
                      extent_id=e["extent_id"], connector="html", tier=e["tier"], languages=tuple(e["languages"]), config=c)
    pats = tuple(re.compile(p) for p in c.get("pdf_link_patterns", []))
    rows = []
    for url, path in idx.items():
        if not any(url.startswith(p) for p in c["allow_prefixes"]):
            continue
        raw = open(path, "rb").read()
        if b"<html" not in raw[:5000].lower():
            continue
        html = raw.decode("utf-8", errors="replace")
        page = parse_crawled_page(html, url, spec, pats)
        status = "emitted" if page.emit and page.sections else ("empty" if page.emit else "not_emitted")
        rows.append((url, status, len(page.sections), page.language, page.title[:50]))
        tot["pages"] += 1; tot[status] += 1
    out[e["id"]] = rows
    bad = [r for r in rows if r[1] != "emitted"]
    if rows:
        print(f"{e['id']:32} saved_pages={len(rows):3} emitted={sum(1 for r in rows if r[1]=='emitted'):3}" +
              (f"  NON-EMITTED: {[(r[0][-60:], r[1], r[3]) for r in bad]}" if bad else ""))
print(tot)
json.dump(out, open(S + "/newpipe/dry_parse_all.json", "w"), indent=0, ensure_ascii=False)
