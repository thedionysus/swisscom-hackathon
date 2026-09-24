"""Print the labelling table for a topic set, to paste into LABELLING.md (so labellers and Jev see the same topics).

  python topics_table.py               the twenty topics in swiss_grounding.corpus.topics (ADR 0007)
  python topics_table.py topics.json   another set: a JSON list of {"id", "label", "covers"}
"""
import json, pathlib, sys

if len(sys.argv) > 1:
    topics = [(t["id"], t["label"], t["covers"]) for t in json.loads(pathlib.Path(sys.argv[1]).read_text())]
else:
    from swiss_grounding.corpus.topics import TOPICS
    topics = [(t.id, t.label, t.covers) for t in TOPICS]
print("| id | Label | Covers |\n|---|---|---|")
for tid, label, covers in topics:
    print(f"| `{tid}` | {label} | {covers} |")
