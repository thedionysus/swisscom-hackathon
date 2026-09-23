from io import BytesIO
from pathlib import Path

import httpx
from pypdf import PdfWriter

from swiss_grounding.corpus.connectors.pdf import MAX_PDF_BYTES, PdfConnector, parse_pdf
from swiss_grounding.corpus.models import DiscoveredPdf, KnownState, SourceSpec

SAMPLE = (Path(__file__).parents[2] / "fixtures" / "sample.pdf").read_bytes()
SPEC = SourceSpec(id="x", name="X", publisher="X", authority="official_info", level="municipal",
                  extent_id="CH-BE-351", connector="html", tier=1, languages=("de",), config={})


def _blank_pdf(width: float = 595, height: float = 842) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def _text_pdf(text: str) -> bytes:
    """A minimal single-page PDF with a real content stream, assembled by hand (no reportlab in
    this repo's deps) so extract_text() returns real text rather than an empty string."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
         b"/MediaBox [0 0 612 792] /Contents 5 0 R >>"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode()
    objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return bytes(out)


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


def test_text_page_with_real_text_is_not_flagged_for_ocr(tmp_path):
    content = _text_pdf("This paragraph has real extractable text, well over eighty characters "
                        "long so it is not mistaken for a scanned page.")
    doc = parse_pdf(content, url="https://x.ch/real.pdf", language="de", title_hint="Real", source_id="x",
                    artifact_path="real", ocr_dir=tmp_path)
    [section] = doc.sections
    assert section.needs_ocr is False
    assert section.text != ""
    assert "real extractable text" in section.text


def test_connector_downloads_and_parses(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=SAMPLE, headers={"content-type": "application/pdf"})))
    result = PdfConnector(client, data_dir=tmp_path, sleep=lambda s: None).run_pdfs(
        SPEC, [DiscoveredPdf("https://x.ch/a.pdf", "de", "Merkblatt", "x")], known={})
    assert len(result.documents) == 1 and result.documents[0].title


def test_known_pdf_answering_404_is_reported_gone(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    known = {"https://x.ch/gone.pdf": KnownState(etag=None, last_modified=None, content_hash="h")}
    result = PdfConnector(client, data_dir=tmp_path, sleep=lambda s: None).run_pdfs(
        SPEC, [DiscoveredPdf("https://x.ch/gone.pdf", "de", "Gone", "x")], known=known)
    assert result.gone_urls == ("https://x.ch/gone.pdf",)
    assert result.documents == ()


def test_pdf_re_check_sends_if_modified_since(tmp_path):
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        return httpx.Response(304)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    known = {"https://x.ch/a.pdf": KnownState(etag=None, last_modified="Mon, 01 Jan 2026 00:00:00 GMT",
                                              content_hash="h")}
    result = PdfConnector(client, data_dir=tmp_path, sleep=lambda s: None).run_pdfs(
        SPEC, [DiscoveredPdf("https://x.ch/a.pdf", "de", "A", "x")], known=known)
    assert seen_headers.get("if-modified-since") == "Mon, 01 Jan 2026 00:00:00 GMT"
    assert result.unchanged_urls == ("https://x.ch/a.pdf",)


def test_download_aborts_past_max_bytes_via_content_length(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=b"x" * 10,
                                 headers={"content-type": "application/pdf",
                                          "content-length": str(MAX_PDF_BYTES + 1)})))
    result = PdfConnector(client, data_dir=tmp_path, sleep=lambda s: None).run_pdfs(
        SPEC, [DiscoveredPdf("https://x.ch/huge.pdf", "de", "Huge", "x")], known={})
    assert result.documents == ()
    assert any("larger than" in reason for _, reason in result.errors)


def test_response_that_is_not_a_pdf_is_rejected(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, text="<html>Login</html>", headers={"content-type": "text/html"})))
    result = PdfConnector(client, data_dir=tmp_path, sleep=lambda s: None).run_pdfs(
        SPEC, [DiscoveredPdf("https://www.ahv-iv.ch/p/2.01.d", "de", "2.01", "x")], known={})
    assert result.documents == ()
    assert result.errors == (("https://www.ahv-iv.ch/p/2.01.d", "not a PDF (content-type text/html)"),)
    assert not list(tmp_path.rglob("*.pdf"))


def test_octet_stream_is_accepted_only_with_pdf_magic_bytes(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        body = SAMPLE if request.url.path.endswith("real") else b"PK\x03\x04zip"
        return httpx.Response(200, content=body, headers={"content-type": "application/octet-stream"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = PdfConnector(client, data_dir=tmp_path, sleep=lambda s: None).run_pdfs(
        SPEC, [DiscoveredPdf("https://x.ch/p/real", "de", "Real", "x"),
               DiscoveredPdf("https://x.ch/p/zip", "de", "Zip", "x")], known={})
    assert [d.url for d in result.documents] == ["https://x.ch/p/real"]
    assert result.errors == (("https://x.ch/p/zip", "not a PDF (content-type application/octet-stream)"),)


def test_metadata_title_whitespace_is_collapsed(tmp_path):
    """Live AHV leaflet: the PDF title metadata holds a carriage return mid-title."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Title": "2.01 - Lohnbeiträge an die\rAHV,  die IV "})
    out = BytesIO()
    writer.write(out)
    doc = parse_pdf(out.getvalue(), url="https://www.ahv-iv.ch/p/2.01.d", language="de", title_hint="x",
                    source_id="x", artifact_path="t", ocr_dir=tmp_path)
    assert doc.title == "2.01 - Lohnbeiträge an die AHV, die IV"
