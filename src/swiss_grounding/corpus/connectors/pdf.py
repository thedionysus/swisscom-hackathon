import hashlib
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pypdfium2 as pdfium
from pypdf import PdfReader

from swiss_grounding.corpus.artifacts import save_artifact
from swiss_grounding.corpus.models import (
    ConnectorResult,
    DiscoveredPdf,
    KnownState,
    ParsedDocument,
    ParsedSection,
    SourceSpec,
)

MIN_TEXT_CHARS = 80
RENDER_SCALE = 150 / 72
MAX_PDF_BYTES = 30_000_000


@contextmanager
def _closing(obj):
    try:
        yield obj
    finally:
        obj.close()


def _render(document: pdfium.PdfDocument, index: int, path: Path) -> tuple[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with (_closing(document[index]) as page, _closing(page.render(scale=RENDER_SCALE)) as bitmap,
          _closing(bitmap.to_pil()) as pil_image):
        pil_image.save(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return str(path), digest


def parse_pdf(content: bytes, *, url: str, language: str, title_hint: str, source_id: str,
              artifact_path: str | None, ocr_dir: Path | str) -> ParsedDocument:
    reader = PdfReader(BytesIO(content))
    meta_title = (reader.metadata.title if reader.metadata and reader.metadata.title else "").strip()
    title = meta_title or title_hint.strip() or Path(urlparse(url).path).name
    stem = Path(artifact_path).stem if artifact_path else Path(urlparse(url).path).stem
    sections = []
    document: pdfium.PdfDocument | None = None
    try:
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            crumbs = (title, f"p. {number}")
            if len(text) < MIN_TEXT_CHARS:
                if document is None:
                    document = pdfium.PdfDocument(content)
                image, digest = _render(document, number - 1,
                                        Path(ocr_dir) / source_id / f"{stem}-p{number}.png")
                sections.append(ParsedSection(align_key=f"{language}:p{number}", breadcrumb=crumbs,
                                              anchor=f"page={number}", text="", needs_ocr=True, ocr_image=image,
                                              ocr_digest=digest))
            else:
                sections.append(ParsedSection(align_key=f"{language}:p{number}", breadcrumb=crumbs,
                                              anchor=f"page={number}", text=text))
    finally:
        if document is not None:
            document.close()
    return ParsedDocument(source_id=source_id, url=url, language=language, work_key=f"pdf:{url}", title=title,
                          sections=tuple(sections), extraction="pdf_text", artifact_path=artifact_path)


class _TooLarge(Exception):
    pass


class PdfConnector:
    def __init__(self, http: httpx.Client, data_dir: Path | str, sleep: Callable[[float], None] = time.sleep,
                 delay_seconds: float = 0.5):
        self._http = http
        self._data_dir = Path(data_dir)
        self._sleep = sleep
        self._delay = delay_seconds

    def _download(self, url: str, headers: dict[str, str]):
        """Stream the response, aborting as soon as MAX_PDF_BYTES is exceeded.

        Returns (status_code, headers, content) with content empty for non-2xx/304 responses.
        """
        with self._http.stream("GET", url, headers=headers, follow_redirects=True, timeout=60) as response:
            if response.status_code >= 300:
                response.close()
                return response.status_code, response.headers, b""
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_PDF_BYTES:
                response.close()
                raise _TooLarge
            body = bytearray()
            for chunk in response.iter_bytes():
                body += chunk
                if len(body) > MAX_PDF_BYTES:
                    response.close()
                    raise _TooLarge
            return response.status_code, response.headers, bytes(body)

    def run_pdfs(self, spec: SourceSpec, pdfs: Sequence[DiscoveredPdf],
                 known: Mapping[str, KnownState]) -> ConnectorResult:
        documents, unchanged, gone, errors = [], [], [], []
        for pdf in pdfs:
            prior = known.get(pdf.url)
            headers = {}
            if prior and prior.etag:
                headers["if-none-match"] = prior.etag
            if prior and prior.last_modified:
                headers["if-modified-since"] = prior.last_modified
            try:
                status, response_headers, content = self._download(pdf.url, headers)
            except _TooLarge:
                errors.append((pdf.url, f"PDF larger than {MAX_PDF_BYTES} bytes"))
                continue
            except httpx.HTTPError as exc:
                errors.append((pdf.url, f"fetch failed: {exc}"))
                continue
            finally:
                self._sleep(self._delay)
            if status == 304:
                unchanged.append(pdf.url)
                continue
            if status in (404, 410):
                if pdf.url in known:
                    gone.append(pdf.url)
                else:
                    errors.append((pdf.url, f"HTTP {status}"))
                continue
            if status >= 400:
                errors.append((pdf.url, f"HTTP {status}"))
                continue
            path = save_artifact(self._data_dir, spec.id, pdf.url, content, ".pdf")
            try:
                doc = parse_pdf(content, url=pdf.url, language=pdf.language, title_hint=pdf.title_hint,
                                source_id=spec.id, artifact_path=path, ocr_dir=self._data_dir / "ocr")
            except Exception as exc:  # noqa: BLE001 - a malformed PDF fails one document, never the run
                errors.append((pdf.url, f"PDF parse failed: {exc}"))
                continue
            documents.append(replace(doc, etag=response_headers.get("etag"),
                                     last_modified=response_headers.get("last-modified"),
                                     retrieved_via=spec.retrieved_via))
        return ConnectorResult(documents=tuple(documents), unchanged_urls=tuple(unchanged), gone_urls=tuple(gone),
                               errors=tuple(errors))
