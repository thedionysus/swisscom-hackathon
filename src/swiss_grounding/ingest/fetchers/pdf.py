import io
from collections.abc import Callable, Mapping

import httpx
from pypdf import PdfReader

from swiss_grounding.ingest.models import (
    FetchedDocument,
    FetchError,
    FetchResult,
    KnownUrl,
    Section,
)
from swiss_grounding.registry.models import Source

PageExtractor = Callable[[bytes], tuple[str, ...]]


def extract_pages_with_pypdf(data: bytes) -> tuple[str, ...]:
    reader = PdfReader(io.BytesIO(data))
    return tuple((page.extract_text() or "").strip() for page in reader.pages)


class PdfFetcher:
    """Fetch configured PDF URLs; HEAD first for change detection, then download and split by page."""

    def __init__(self, http: httpx.Client, extract_pages: PageExtractor = extract_pages_with_pypdf):
        self._http = http
        self._extract = extract_pages

    def fetch(self, source: Source, known: Mapping[str, KnownUrl]) -> FetchResult:
        urls = tuple(source.fetch_config.get("urls", ()))
        language = source.fetch_config.get("language", "de")
        documents, unchanged, gone, errors = [], [], [], []
        for url in urls:
            try:
                head = self._http.head(url, follow_redirects=True)
                if head.status_code in (404, 410):
                    if url in known:
                        gone.append(url)
                    continue
                last_modified = head.headers.get("last-modified")
                prior = known.get(url)
                if prior and last_modified and prior.last_modified == last_modified:
                    unchanged.append(url)
                    continue
                response = self._http.get(url, follow_redirects=True)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                errors.append(FetchError(url=url, reason=str(exc)))
                continue
            try:
                pages = self._extract(response.content)
            except Exception as exc:  # noqa: BLE001 - pypdf can raise arbitrary exceptions on bad input
                errors.append(FetchError(url=url, reason=str(exc)))
                continue
            sections = tuple(
                Section(heading_path=f"Page {i}", anchor=f"page={i}", text=text)
                for i, text in enumerate(pages, 1) if text
            )
            if not sections:
                errors.append(FetchError(url=url, reason="no extractable text"))
                continue
            documents.append(FetchedDocument(
                source_id=source.id, url=url, title=url.rsplit("/", 1)[-1], language=language,
                sections=sections, etag=head.headers.get("etag"), last_modified=last_modified,
            ))
        return FetchResult(documents=tuple(documents), unchanged_urls=tuple(unchanged),
                            gone_urls=tuple(gone), errors=tuple(errors))
