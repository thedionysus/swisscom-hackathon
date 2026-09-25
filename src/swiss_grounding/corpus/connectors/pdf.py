import hashlib
import logging
import re
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
import pypdfium2 as pdfium
from pypdf import PdfReader

from swiss_grounding.corpus.artifacts import save_artifact
from swiss_grounding.corpus.connectors.politeness import (
    SHARED_THROTTLE,
    FetchResult,
    HostThrottle,
    request_with_backoff,
)
from swiss_grounding.corpus.models import (
    ConnectorResult,
    DiscoveredPdf,
    KnownState,
    ParsedDocument,
    ParsedSection,
    SourceSpec,
)

# pypdf logs a "fontTools is required for..." warning on every page of many real-world PDFs;
# it is noise for us (we never need the missing metrics), so it is downgraded below WARNING.
logging.getLogger("pypdf").setLevel(logging.ERROR)

MIN_TEXT_CHARS = 80
RENDER_SCALE = 150 / 72
MAX_PDF_BYTES = 30_000_000
# Servers that label a download generically: accepted only when the body starts like a PDF.
GENERIC_CONTENT_TYPES = frozenset({"", "application/octet-stream", "binary/octet-stream", "application/download",
                                   "application/force-download", "application/x-download"})
PDF_MAGIC_WINDOW = 1024
_FILE_NAME = re.compile(r"\.(?:pdf|docx?|dotx?|xlsx?|pptx?|indd|qxp|qxd|rtf|odt|ods|txt|html?|tiff?|jpe?g|png|eps|ai)$"
                        r"|^Microsoft (?:Word|Excel|PowerPoint) - ", re.IGNORECASE)
_TEMPLATE_NAME = re.compile(r"^(?:leer|untitled|unbenannt|ohne titel|sans titre|senza titolo|titel|title|titre|titolo"
                            r"|vorlage|template|dokument|document|documento)\s*\d*$|^_.*_$", re.IGNORECASE)


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


def _file_or_template_name(title: str) -> bool:
    """A title that names a file or a template rather than the document: "Leer", "Dokument1",
    "Ferienplan_2026.indd", "Microsoft Word - Tarif.docx", "_ERZIEHUNGSDIREKTION_"."""
    return bool(_FILE_NAME.search(title) or _TEMPLATE_NAME.match(title))


def _pdf_title(meta_title: str, title_hint: str, url: str) -> str:
    """The metadata title, unless it names a file or a template (11 of 21 metadata titles in the Run 3
    PDFs were junk, #57); then the link text; then either one as it is; then the URL-decoded file name."""
    good = [t for t in (meta_title, title_hint) if t and not _file_or_template_name(t)]
    return (good or [t for t in (title_hint, meta_title) if t] or [unquote(Path(urlparse(url).path).name)])[0]


def parse_pdf(content: bytes, *, url: str, language: str, title_hint: str, source_id: str,
              artifact_path: str | None, ocr_dir: Path | str) -> ParsedDocument:
    reader = PdfReader(BytesIO(content))
    meta_title = " ".join((reader.metadata.title if reader.metadata and reader.metadata.title else "").split())
    title = _pdf_title(meta_title, " ".join(title_hint.split()), url)
    stem = Path(artifact_path).stem if artifact_path else Path(urlparse(url).path).stem
    sections = []
    document: pdfium.PdfDocument | None = None
    try:
        for number, page in enumerate(reader.pages, start=1):
            # PostgreSQL text columns reject NUL bytes; some scanned/OCR'd PDFs embed them in
            # their text layer, so strip them at extraction, the earliest point we see them.
            text = (page.extract_text() or "").replace("\x00", "").strip()
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


class _NotPdf(Exception):
    def __init__(self, content_type: str):
        super().__init__(f"not a PDF (content-type {content_type or 'missing'})")


def _media_type(headers: httpx.Headers) -> str:
    return headers.get("content-type", "").split(";")[0].strip().lower()


class PdfConnector:
    def __init__(self, http: httpx.Client, data_dir: Path | str, sleep: Callable[[float], None] = time.sleep,
                 delay_seconds: float = 0.5, throttle: HostThrottle | None = None):
        self._http = http
        self._data_dir = Path(data_dir)
        self._sleep = sleep
        self._delay = delay_seconds
        self._throttle = throttle or SHARED_THROTTLE

    def _before(self, url: str) -> None:
        self._throttle.wait(url, self._delay, self._sleep)

    def _download(self, url: str, headers: dict[str, str], limit: int = MAX_PDF_BYTES) -> FetchResult:
        """Stream the response, aborting as soon as `limit` bytes (the source's `max_pdf_bytes`,
        default MAX_PDF_BYTES) are exceeded.

        The body is empty for a non-2xx/304 response, so a 429/503 can be inspected by
        request_with_backoff without reading (and discarding) a body.
        """
        with self._http.stream("GET", url, headers=headers, follow_redirects=True, timeout=60) as response:
            if response.status_code >= 300:
                response.close()
                return FetchResult(response.status_code, response.headers)
            # Links matched by pdf_link_patterns carry no .pdf suffix, so the response type is the
            # only proof of a PDF; an HTML login page or error shell must not reach the parser.
            media_type = _media_type(response.headers)
            if "pdf" not in media_type and media_type not in GENERIC_CONTENT_TYPES:
                response.close()
                raise _NotPdf(media_type)
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > limit:
                response.close()
                raise _TooLarge
            body = bytearray()
            for chunk in response.iter_bytes():
                body += chunk
                if len(body) > limit:
                    response.close()
                    raise _TooLarge
            if "pdf" not in media_type and b"%PDF" not in body[:PDF_MAGIC_WINDOW]:
                raise _NotPdf(media_type)
            return FetchResult(response.status_code, response.headers, bytes(body))

    def run_pdfs(self, spec: SourceSpec, pdfs: Sequence[DiscoveredPdf],
                 known: Mapping[str, KnownState]) -> ConnectorResult:
        documents, unchanged, gone, errors = [], [], [], []
        limit = int(spec.config.get("max_pdf_bytes", MAX_PDF_BYTES))
        for pdf in pdfs:
            prior = known.get(pdf.url)
            headers = {}
            if prior and prior.etag:
                headers["if-none-match"] = prior.etag
            if prior and prior.last_modified:
                headers["if-modified-since"] = prior.last_modified
            try:
                fetched = request_with_backoff(pdf.url, self._throttle, self._before,
                                               lambda u=pdf.url, h=headers: self._download(u, h, limit), self._sleep)
            except _TooLarge:
                errors.append((pdf.url, f"PDF larger than {limit} bytes"))
                continue
            except _NotPdf as exc:
                errors.append((pdf.url, str(exc)))
                continue
            except httpx.HTTPError as exc:
                errors.append((pdf.url, f"fetch failed: {exc}"))
                continue
            status, response_headers, content = fetched.status_code, fetched.headers, fetched.body
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
