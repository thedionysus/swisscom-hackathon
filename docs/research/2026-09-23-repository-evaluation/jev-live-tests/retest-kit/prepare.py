"""Split the corpus export into what the labellers and Jev see, and the production baseline they must not see.

In:  chunks_with_baseline.json (export_sample.sql)
Out: chunks.json   [{id, language, page_title, heading, text}]  -> labellers and run_retest.py
     baseline.json {id: {topics, boilerplate}}                    -> score_retest.py only
"""
import json, pathlib, sys

rows = json.loads(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "chunks_with_baseline.json").read_text())
blind = [{k: r[k] for k in ("id", "language", "page_title", "heading", "text")} for r in rows]
base = {r["id"]: {"topics": r["production_topics"] or [], "boilerplate": bool(r["production_boilerplate"])} for r in rows}
pathlib.Path("chunks.json").write_text(json.dumps(blind, ensure_ascii=False, indent=1))
pathlib.Path("baseline.json").write_text(json.dumps(base, ensure_ascii=False, indent=1))
print(f"{len(blind)} chunks; languages {sorted({r['language'] for r in rows})}; "
      f"production boilerplate {sum(b['boilerplate'] for b in base.values())}")
