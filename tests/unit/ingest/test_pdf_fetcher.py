from pathlib import Path

import httpx

from swiss_grounding.ingest.fetchers.pdf import PdfFetcher
from swiss_grounding.ingest.models import KnownUrl
from swiss_grounding.registry.models import Source

PDF_BYTES = (Path(__file__).parent.parent.parent / "fixtures" / "sample.pdf").read_bytes()


def source():
    return Source(id="zh_as", name="AS", base_url="https://www.stadt-zuerich.ch",
                  default_extent_id="CH-ZH-261", authority="municipal_law", categories=("dogs",),
                  fetch_strategy="pdf",
                  fetch_config={"urls": ["https://www.stadt-zuerich.ch/as/hunde.pdf"], "language": "de"})


def make(handler, pages=("Art. 1 Hunde sind anzumelden.", "Art. 2 Leinenpflicht in Parks.")):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return PdfFetcher(http=http, extract_pages=lambda data: tuple(pages))


def test_downloads_and_splits_pages_into_sections():
    def handler(request):
        if request.method == "HEAD":
            return httpx.Response(200, headers={"content-length": str(len(PDF_BYTES)), "last-modified": "L1"})
        return httpx.Response(200, content=PDF_BYTES, headers={"content-type": "application/pdf"})

    result = make(handler).fetch(source(), {})
    doc = result.documents[0]
    assert doc.url.endswith("hunde.pdf") and doc.language == "de"
    assert [s.heading_path for s in doc.sections] == ["Page 1", "Page 2"]
    assert doc.sections[1].text.startswith("Art. 2")
    assert doc.last_modified == "L1"


def test_head_unchanged_skips_download():
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, headers={"content-length": "10", "last-modified": "L1"})

    known = {"https://www.stadt-zuerich.ch/as/hunde.pdf": KnownUrl(etag=None, last_modified="L1", content_hash="h")}
    result = make(handler).fetch(source(), known)
    assert result.unchanged_urls == ("https://www.stadt-zuerich.ch/as/hunde.pdf",)
    assert calls == ["HEAD"]


def test_404_on_known_url_is_gone():
    def handler(request):
        return httpx.Response(404)

    known = {"https://www.stadt-zuerich.ch/as/hunde.pdf": KnownUrl(None, None, "h")}
    result = make(handler).fetch(source(), known)
    assert result.gone_urls == ("https://www.stadt-zuerich.ch/as/hunde.pdf",)


def test_extraction_failure_is_an_error():
    def handler(request):
        if request.method == "HEAD":
            return httpx.Response(200)
        return httpx.Response(200, content=b"not a pdf")

    http = httpx.Client(transport=httpx.MockTransport(handler))

    def broken(data):
        raise ValueError("bad pdf")

    result = PdfFetcher(http=http, extract_pages=broken).fetch(source(), {})
    assert result.documents == () and "bad pdf" in result.errors[0].reason


def test_real_pypdf_extractor_reads_blank_fixture_without_error():
    from swiss_grounding.ingest.fetchers.pdf import extract_pages_with_pypdf

    pages = extract_pages_with_pypdf(PDF_BYTES)
    assert len(pages) == 2 and all(p == "" for p in pages)
