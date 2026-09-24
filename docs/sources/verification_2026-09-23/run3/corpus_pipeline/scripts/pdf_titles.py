"""Run the NEW parse_pdf on PDFs the Run 3 agents saved (offline): title source, pages, pages needing OCR."""
import json, os, shutil
from swiss_grounding.corpus.connectors.pdf import parse_pdf
S = "<scratchpad>"
idx = json.load(open(S + "/newpipe/saved_index.json"))
OCR = S + "/newpipe/_ocrtest"
hints = {  # link text seen on the parent pages in pdf_discovery_results.txt (empty when unknown)
    "https://www.neuchatelville.ch/fileadmin/sites/ne_ville/fichiers/votre_commune/reglementation/12_21_A_interChiens.pdf": "",
}
for url, path in sorted(idx.items()):
    raw = open(path, "rb").read()
    if not raw.startswith(b"%PDF"):
        continue
    try:
        doc = parse_pdf(raw, url=url, language="de", title_hint=hints.get(url, ""), source_id="t", artifact_path=None, ocr_dir=OCR)
    except Exception as exc:
        print(f"{url}\n    parse failed: {exc!r}"); continue
    ocr = sum(1 for s in doc.sections if s.needs_ocr)
    from pypdf import PdfReader
    from io import BytesIO
    meta = PdfReader(BytesIO(raw)).metadata
    mt = (meta.title if meta and meta.title else "")
    print(f"{url[:120]}\n    title={doc.title[:70]!r} (pdf metadata title={mt[:50]!r}) pages={len(doc.sections)} needs_ocr={ocr} bytes={len(raw)}")
shutil.rmtree(OCR, ignore_errors=True)
