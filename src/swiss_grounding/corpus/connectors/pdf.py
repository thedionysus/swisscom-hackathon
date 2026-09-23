import hashlib
import time
from collections.abc import Callable, Mapping, Sequence
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


def _render(content: bytes, index: int, path: Path) -> tuple[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(content)
    document[index].render(scale=RENDER_SCALE).to_pil().save(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return str(path), digest


def parse_pdf(content: bytes, *, url: str, language: str, title_hint: str, source_id: str,
              artifact_path: str | None, ocr_dir: Path | str) -> ParsedDocument:
    reader = PdfReader(BytesIO(content))
    meta_title = (reader.metadata.title if reader.metadata and reader.metadata.title else "").strip()
    title = meta_title or title_hint.strip() or Path(urlparse(url).path).name
    stem = Path(artifact_path).stem if artifact_path else Path(urlparse(url).path).stem
    sections = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        crumbs = (title, f"p. {number}")
        if len(text) < MIN_TEXT_CHARS:
            image, digest = _render(content, number - 1, Path(ocr_dir) / source_id / f"{stem}-p{number}.png")
            sections.append(ParsedSection(align_key=f"{language}:p{number}", breadcrumb=crumbs,
                                          anchor=f"page={number}", text="", needs_ocr=True, ocr_image=image,
                                          ocr_digest=digest))
        else:
            sections.append(ParsedSection(align_key=f"{language}:p{number}", breadcrumb=crumbs,
                                          anchor=f"page={number}", text=text))
    return ParsedDocument(source_id=source_id, url=url, language=language, work_key=f"pdf:{url}", title=title,
                          sections=tuple(sections), extraction="pdf_text", artifact_path=artifact_path)


class PdfConnector:
    def __init__(self, http: httpx.Client, data_dir: Path | str, sleep: Callable[[float], None] = time.sleep,
                 delay_seconds: float = 0.5):
        self._http = http
        self._data_dir = Path(data_dir)
        self._sleep = sleep
        self._delay = delay_seconds

    def run_pdfs(self, spec: SourceSpec, pdfs: Sequence[DiscoveredPdf],
                 known: Mapping[str, KnownState]) -> ConnectorResult:
        documents, unchanged, errors = [], [], []
        for pdf in pdfs:
            prior = known.get(pdf.url)
            headers = {"if-none-match": prior.etag} if prior and prior.etag else {}
            try:
                response = self._http.get(pdf.url, headers=headers, follow_redirects=True, timeout=60)
            except httpx.HTTPError as exc:
                errors.append((pdf.url, f"fetch failed: {exc}"))
                continue
            finally:
                self._sleep(self._delay)
            if response.status_code == 304:
                unchanged.append(pdf.url)
                continue
            if response.status_code >= 400:
                errors.append((pdf.url, f"HTTP {response.status_code}"))
                continue
            if len(response.content) > MAX_PDF_BYTES:
                errors.append((pdf.url, f"PDF larger than {MAX_PDF_BYTES} bytes"))
                continue
            path = save_artifact(self._data_dir, spec.id, pdf.url, response.content, ".pdf")
            try:
                doc = parse_pdf(response.content, url=pdf.url, language=pdf.language, title_hint=pdf.title_hint,
                                source_id=spec.id, artifact_path=path, ocr_dir=self._data_dir / "ocr")
            except Exception as exc:  # noqa: BLE001 - a malformed PDF fails one document, never the run
                errors.append((pdf.url, f"PDF parse failed: {exc}"))
                continue
            documents.append(replace(doc, etag=response.headers.get("etag"),
                                     last_modified=response.headers.get("last-modified"),
                                     retrieved_via=spec.retrieved_via))
        return ConnectorResult(documents=tuple(documents), unchanged_urls=tuple(unchanged), errors=tuple(errors))
