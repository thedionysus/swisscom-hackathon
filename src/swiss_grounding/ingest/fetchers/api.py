from collections.abc import Callable, Mapping
from datetime import date
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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


def _record_id(cfg: dict, record: dict) -> str:
    """Composite id via id_template ("{waste_type}-{date}") or a single id_field (default "id")."""
    if "id_template" in cfg:
        return _render(cfg["id_template"], record)
    return str(record.get(cfg.get("id_field", "id"), ""))


def _request_url(template: str, today: date) -> str:
    """Render date placeholders ({today} as ISO date) so calendar feeds anchor to the present."""
    return template.replace("{today}", today.isoformat())


def _is_placeholder(value: str) -> bool:
    return "{" in value and "}" in value


def _identity_url(template: str) -> str:
    """The feed URL with placeholder query parameters removed: stable across days and a working link."""
    parts = urlsplit(template)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_placeholder(v)]
    return urlunsplit(parts._replace(query=urlencode(kept)))


def _event_date(cfg: dict, record: dict) -> date | None:
    """ISO date from the configured event_date_field; None when absent or unparseable."""
    field = cfg.get("event_date_field")
    if not field:
        return None
    try:
        return date.fromisoformat(str(record.get(field, "")))
    except ValueError:
        return None


class ApiFetcher:
    """Turn each record of a JSON feed into a small document, keyed by feed URL + record id.

    The configured URL may contain ``{today}``; it is rendered for the HTTP request only.
    Document identity uses the URL without placeholder parameters so records stay stable as the
    window moves and the stored url remains a working link.
    """

    def __init__(self, http: httpx.Client, today: Callable[[], date] = date.today):
        self._http = http
        self._today = today

    def fetch(self, source: Source, known: Mapping[str, KnownUrl]) -> FetchResult:
        cfg = source.fetch_config
        request_url = _request_url(cfg["url"], self._today())
        feed_url = _identity_url(cfg["url"])
        try:
            response = self._http.get(request_url)
            response.raise_for_status()
            records = _dig(response.json(), cfg.get("records_path", ""))
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return FetchResult(documents=(), errors=(FetchError(url=request_url, reason=str(exc)),))
        documents, errors = [], []
        for record in records:
            url = None
            try:
                record_id = _record_id(cfg, record)
                if not record_id:
                    continue
                url = f"{feed_url}#{record_id}"
                title = _render(cfg["title_template"], record)
                text = _render(cfg["text_template"], record)
            except ValueError as exc:
                errors.append(FetchError(url=url or feed_url, reason=str(exc)))
                continue
            documents.append(FetchedDocument(
                source_id=source.id, url=url, identifier=record_id, title=title,
                language=cfg.get("language", "en"),
                sections=(Section(heading_path=title, anchor=None, text=text),),
                event_date=_event_date(cfg, record),
            ))
        present = {d.url for d in documents}
        gone = tuple(u for u in known if u.startswith(feed_url + "#") and u not in present)
        return FetchResult(documents=tuple(documents), gone_urls=gone, errors=tuple(errors))
