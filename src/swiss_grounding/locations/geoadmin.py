import re
from dataclasses import dataclass

import httpx

TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class GeoAdminHit:
    bfs_id: int
    label: str


class GeoAdminClient:
    """Thin client for the swisstopo SearchServer. Only commune hits (origin gg25) are returned."""

    def __init__(self, http: httpx.Client):
        self._http = http

    @classmethod
    def from_settings(cls, base_url: str, timeout_seconds: float,
                      transport: httpx.BaseTransport | None = None) -> "GeoAdminClient":
        return cls(http=httpx.Client(base_url=base_url, timeout=timeout_seconds, transport=transport))

    def search_communes(self, text: str) -> tuple[GeoAdminHit, ...]:
        try:
            response = self._http.get(
                "/rest/services/api/SearchServer",
                params={"searchText": text, "type": "locations", "origins": "gg25", "limit": 5},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError(f"GeoAdmin lookup failed for {text!r}: {exc}") from exc
        hits: list[GeoAdminHit] = []
        for item in payload.get("results", []):
            attrs = item.get("attrs", {})
            if attrs.get("origin") != "gg25":
                continue
            try:
                bfs_id = int(attrs["featureId"])
                label = TAG_RE.sub("", attrs["label"]).strip()
            except (KeyError, TypeError, ValueError):
                continue
            hits.append(GeoAdminHit(bfs_id=bfs_id, label=label))
        return tuple(hits)
