from collections.abc import Mapping
from typing import Any

import httpx

from swiss_grounding.ingest.models import (
    FetchedDocument,
    FetchError,
    FetchResult,
    KnownUrl,
    Section,
)
from swiss_grounding.registry.models import Source


def _dig(payload: Any, dotted: str) -> list:
    node = payload
    if dotted:
        for key in dotted.split("."):
            if not isinstance(node, dict) or key not in node:
                raise ValueError(f"records_path {dotted!r} not found in payload")
            node = node[key]
    if not isinstance(node, list):
        raise TypeError(f"records_path {dotted!r} does not point to a list")
    return node


def _render(template: str, record: dict) -> str:
    try:
        return template.format_map(record).strip()
    except KeyError as exc:
        raise ValueError(f"record is missing template field {exc}") from exc


class ApiFetcher:
    """Turn each record of a JSON feed into a small document, keyed by feed URL + record id."""

    def __init__(self, http: httpx.Client):
        self._http = http

    def fetch(self, source: Source, known: Mapping[str, KnownUrl]) -> FetchResult:
        cfg = source.fetch_config
        feed_url = cfg["url"]
        try:
            response = self._http.get(feed_url)
            response.raise_for_status()
            records = _dig(response.json(), cfg.get("records_path", ""))
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return FetchResult(documents=(), errors=(FetchError(url=feed_url, reason=str(exc)),))
        documents, errors = [], []
        for record in records:
            record_id = str(record.get(cfg.get("id_field", "id"), ""))
            if not record_id:
                continue
            url = f"{feed_url}#{record_id}"
            try:
                title = _render(cfg["title_template"], record)
                text = _render(cfg["text_template"], record)
            except ValueError as exc:
                errors.append(FetchError(url=url, reason=str(exc)))
                continue
            documents.append(FetchedDocument(
                source_id=source.id, url=url, identifier=record_id, title=title,
                language=cfg.get("language", "en"),
                sections=(Section(heading_path=title, anchor=None, text=text),),
            ))
        present = {d.url for d in documents}
        gone = tuple(u for u in known if u.startswith(feed_url + "#") and u not in present)
        return FetchResult(documents=tuple(documents), gone_urls=gone, errors=tuple(errors))
