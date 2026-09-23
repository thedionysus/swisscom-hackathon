#!/usr/bin/env python3
"""Resolve official URLs for key laws: LexFind texts-of-law/{id} (VD NE GE JU) and LexWork bdlf.fr.ch (FR)."""
import json
import re
import subprocess
import time

UA = "Mozilla/5.0 swiss-grounding-check"

LEXFIND = {
    "VD": [(20131, "270.11.5 TFJC"), (24158, "133.75 LPolC"), (24169, "133.75.1 RLPolC"), (19058, "652.31.1 dog tax"),
           (20913, "642.11 LI"), (20181, "170.551 FAO decree"), (24290, "400.02 LEO"), (19064, "173.01 LOJV"),
           (19128, "741.15.1 SAN fees"), (18895, "173.655 LJB"), (23776, "132.15 decoupage")],
    "NE": [(11563, "164.1 LTFrais"), (11404, "636.20 LChiens"), (10974, "636.201 RELChiens"), (10823, "631.0 LCdir"),
           (11353, "161.1 OJN"), (11839, "150.20 LPAO"), (10648, "761.43 SCAN fees")],
    "GE": [(31872, "E 1 05.10 RTFMC"), (31214, "M 3 45 LChiens"), (30879, "M 3 45.01 RChiens"), (31836, "D 3 08 LIPP"),
           (31117, "B 2 10 LFAO"), (31181, "E 3 15 LCCBL"), (31534, "H 1 05.08 OCV fees"), (31050, "E 2 05 LOJ"),
           (31331, "C 1 10 LIP")],
    "JU": [(9346, "176.511 emoluments judiciaires"), (8706, "645.1 taxe chiens"), (9090, "645.11 ord taxe chiens"),
           (9034, "641.11 Loi d'impot"), (9521, "170.513 JO"), (9219, "182.351 conciliation bail"), (8887, "410.11 LEO"),
           (9277, "741.11 LCR"), (8719, "181.1 LOJ"), (9464, "190.11 communes")],
}
LEXWORK_FR = ["130.11", "130.16", "725.3", "725.31", "631.1", "781.16", "124.21", "112.51", "411.0.1", "130.1"]


def get(url):
    r = subprocess.run(["curl", "-s", "--max-time", "60", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    return code, body


for canton, items in LEXFIND.items():
    print("=====", canton)
    for tid, label in items:
        code, body = get(f"https://www.lexfind.ch/api/fe/de/texts-of-law/{tid}")
        try:
            d = json.loads(body)
            urls = [(u.get("language"), u.get("original_url")) for u in d.get("dta_urls", [])]
            print(f"  {code} {d.get('systematic_number')} active={d.get('is_active')} | {label} | {urls}")
        except Exception as e:  # noqa
            print(f"  {code} {tid} {label} parse error {e} {body[:120]}")
        time.sleep(0.3)

print("===== FR (LexWork bdlf.fr.ch)")
for nr in LEXWORK_FR:
    code, body = get(f"https://bdlf.fr.ch/api/fr/texts_of_law/{nr}")
    try:
        d = json.loads(body)
        t = d.get("text_of_law", d)
        sv = t.get("selected_version") or {}
        dates = {k: t.get(k) for k in ("enactment", "date_of_decision") if t.get(k)}
        vd = {k: sv.get(k) for k in sv if re.search(r"date|since|valid|active", k) and isinstance(sv.get(k), str)}
        print(f"  {code} {nr} | {t.get('title')} | abbr={t.get('abbreviation')} | {t.get('canonical_link')} | "
              f"abrogated={t.get('abrogated')} | {dates} | {vd} | {len(body)}B")
    except Exception as e:  # noqa
        print(f"  {code} {nr} parse error {e} {body[:120]}")
    time.sleep(0.3)
