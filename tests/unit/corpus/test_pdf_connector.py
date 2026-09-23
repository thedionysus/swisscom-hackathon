from io import BytesIO
from pathlib import Path

import httpx
from pypdf import PdfWriter

from swiss_grounding.corpus.connectors.pdf import PdfConnector, parse_pdf
from swiss_grounding.corpus.models import DiscoveredPdf, SourceSpec

SAMPLE = (Path(__file__).parents[2] / "fixtures" / "sample.pdf").read_bytes()
SPEC = SourceSpec(id="x", name="X", publisher="X", authority="official_info", level="municipal",
                  extent_id="CH-BE-351", connector="html", tier=1, languages=("de",), config={})


def _blank_pdf(width: float = 595, height: float = 842) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def test_text_pdf_has_one_section_per_page(tmp_path):
    doc = parse_pdf(SAMPLE, url="https://x.ch/a.pdf", language="de", title_hint="Merkblatt", source_id="x",
                    artifact_path="a", ocr_dir=tmp_path)
    assert doc.extraction == "pdf_text"
    assert doc.sections and all(not s.needs_ocr for s in doc.sections if s.text)
    assert doc.sections[0].anchor == "page=1"
    assert doc.sections[0].breadcrumb[-1] == "p. 1"
    assert doc.work_key == "pdf:https://x.ch/a.pdf"


def test_blank_page_is_flagged_for_ocr_and_rendered(tmp_path):
    doc = parse_pdf(_blank_pdf(), url="https://x.ch/scan.pdf", language="de", title_hint="Scan", source_id="x",
                    artifact_path="a", ocr_dir=tmp_path)
    [section] = doc.sections
    assert section.needs_ocr and section.text == ""
    assert Path(section.ocr_image).exists()


def test_ocr_digest_is_sha256_of_rendered_png_and_differs_per_image(tmp_path):
    small = parse_pdf(_blank_pdf(200, 300), url="https://x.ch/small.pdf", language="de", title_hint="Small",
                      source_id="x", artifact_path="small", ocr_dir=tmp_path)
    large = parse_pdf(_blank_pdf(1000, 1400), url="https://x.ch/large.pdf", language="de", title_hint="Large",
                      source_id="x", artifact_path="large", ocr_dir=tmp_path)
    [small_section] = small.sections
    [large_section] = large.sections
    assert small_section.ocr_digest is not None
    assert large_section.ocr_digest is not None
    assert small_section.ocr_digest != large_section.ocr_digest
    import hashlib
    assert small_section.ocr_digest == hashlib.sha256(Path(small_section.ocr_image).read_bytes()).hexdigest()


def test_connector_downloads_and_parses(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=SAMPLE, headers={"content-type": "application/pdf"})))
    result = PdfConnector(client, data_dir=tmp_path, sleep=lambda s: None).run_pdfs(
        SPEC, [DiscoveredPdf("https://x.ch/a.pdf", "de", "Merkblatt", "x")], known={})
    assert len(result.documents) == 1 and result.documents[0].title
