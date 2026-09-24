"""Seeded sample: 20 random sections per source + 15 'targeted' sections whose text hits keywords of >= 2 categories."""
import json, random, re, pathlib
HERE = pathlib.Path(__file__).parent
pages = json.loads((HERE / "pages.json").read_text())
KW = {"hiking": r"wander|wald|natur|park|randonn|forêt|nature|parc", "waste": r"abfall|entsorg|recycl|kehricht|grüngut|déchet|tri sélectif",
      "dogs": r"\bhund|tierhalt|chien|animaux", "taxes": r"steuer|impôt|\btaxe", "housing": r"baubewillig|wohn|miet|bauzone|logement|permis de construire|construction",
      "transport": r"verkehr|velo|tram|\bbus|mobilit|transport|vélo", "parking": r"parkier|parkpl|stationn|parking", "schools": r"schul|bildung|école|scolaire",
      "health": r"gesundheit|spital|santé|hôpital|médic", "safety": r"polizei|sicherheit|notfall|police|sécurité|urgence"}
rows = []
for d in pages:
    for i, s in enumerate(d["sections"]):
        rows.append({"id": f"{d['source']}#{len(rows)}", "source": d["source"], "language": d["language"], "url": d["url"],
                     "page_title": d["title"], "heading_path": s["heading_path"], "text": s["text"][:1500], "truncated": len(s["text"]) > 1500})
rng = random.Random(20260923)
pick, taken = [], set()
for src in ("stadt_zuerich", "ge_ville", "zh_ch"):
    pool = [r for r in rows if r["source"] == src]
    for r in rng.sample(pool, min(20, len(pool))):
        pick.append(dict(r, targeted=False)); taken.add(r["id"])
multi = [r for r in rows if r["id"] not in taken and len(r["text"]) >= 150 and
         sum(bool(re.search(p, r["text"].lower())) for p in KW.values()) >= 2]
for r in rng.sample(multi, min(15, len(multi))):
    pick.append(dict(r, targeted=True))
rng.shuffle(pick)
(HERE / "chunks.json").write_text(json.dumps(pick, ensure_ascii=False, indent=1))
# the file labelers receive: no source-level hints beyond what a crawler sees
blind = [{k: r[k] for k in ("id", "language", "page_title", "heading_path", "text")} for r in pick]
(HERE / "chunks_for_labelling.json").write_text(json.dumps(blind, ensure_ascii=False, indent=1))
print(len(pick), "chunks;", sum(r["targeted"] for r in pick), "targeted; by source:",
      {s: sum(r["source"] == s for r in pick) for s in ("stadt_zuerich", "ge_ville", "zh_ch")}, "| multi-keyword pool:", len(multi))
