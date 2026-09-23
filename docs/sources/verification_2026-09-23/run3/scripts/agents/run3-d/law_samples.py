#!/usr/bin/env python3
"""Fetch fee ordinances and print a CHF sample + format evidence."""
import html
import io
import json
import re
import subprocess
import time

from pypdf import PdfReader

UA = "Mozilla/5.0 swiss-grounding-check"
OUT = "<scratchpad>/run3-d/laws/"
subprocess.run(["mkdir", "-p", OUT])
MONEY = re.compile(r".{0,140}(\d[\d' ]*(?:\.\d+)? ?(?:francs|fr\.)|Fr\.? ?\d[\d'.]*|CHF ?\d[\d'.]*).{0,90}", re.I)


def get(url, fn):
    r = subprocess.run(["curl", "-sL", "--max-time", "90", "-A", UA, "-o", OUT + fn, "-w",
                        "%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}", url],
                       capture_output=True, text=True)
    return r.stdout.split("\t")


def pdf_sample(fn, pat=None):
    r = PdfReader(OUT + fn)
    t = re.sub(r"\s+", " ", " ".join((p.extract_text() or "") for p in r.pages))
    m = re.search(pat, t, re.I) if pat else MONEY.search(t)
    return len(r.pages), len(t), (m.group(0) if m else None)


PDFS = [
    ("NE 164.1 LTFrais", "https://rsn.ne.ch/DATA/program/books/rsne/pdf/164.1.pdf", "ne_164_1.pdf", r".{0,160}conciliation.{0,160}"),
    ("NE 761.43 SCAN fees", "https://rsn.ne.ch/DATA/program/books/rsne/pdf/761.43.pdf", "ne_761_43.pdf", None),
    ("NE 636.20 LChiens", "https://rsn.ne.ch/DATA/program/books/rsne/pdf/636.20.pdf", "ne_636_20.pdf", r".{0,120}laisse.{0,160}"),
    ("GE E 1 05.10 RTFMC", "https://silgeneve.ch/legis/program/books/RSG/pdf/rsg_e1_05p10.pdf", "ge_e1_05p10.pdf", r".{0,160}conciliation.{0,160}"),
    ("JU 176.511 emoluments judiciaires", "https://rsju.jura.ch/fr/viewdocument.html?idn=20021&id=34172&download=1", "ju_176_511.pdf", None),
    ("JU 645.1 taxe chiens", "https://rsju.jura.ch/fr/viewdocument.html?idn=20117&id=26739&download=1", "ju_645_1.pdf", None),
]
for label, url, fn, pat in PDFS:
    code, ct, size, final = get(url, fn)
    try:
        pages, chars, s = pdf_sample(fn, pat)
        print(f"{label}: {code} {ct} {size}B pages={pages} chars={chars}\n   SAMPLE: {s}")
    except Exception as e:  # noqa
        print(f"{label}: {code} {ct} {size}B {final} -> not a readable PDF ({e})")
        print("   head:", open(OUT + fn, "rb").read(300))
    time.sleep(0.5)

# FR 130.11 (LexWork JSON): sample around "émolument de conciliation"
code, ct, size, final = get("https://bdlf.fr.ch/api/fr/texts_of_law/130.11", "fr_130_11.json")
d = json.load(open(OUT + "fr_130_11.json"))
x = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", json.dumps(d, ensure_ascii=False).replace("\\n", " "))))
m = re.search(r"émolument de conciliation.{0,120}", x)
print(f"FR 130.11 RJ: {code} {ct} {size}B\n   SAMPLE: {m.group(0) if m else None}")

# VD 270.11.5 TFJC via BLV API (ladder: the LexFind original_url is the Angular app)
code, ct, size, final = get("https://prestations.vd.ch/pub/blv-publication/api/actes/CONSOLIDE?id=5848c893-424d-4a98-8f8d-a613dcd497b9&cote=270.11.5", "vd_tfjc_meta.json")
print(f"VD 270.11.5 BLV meta: {code} {ct} {size}B {final}")
raw = open(OUT + "vd_tfjc_meta.json", "rb").read()
print("   head:", raw[:400])
