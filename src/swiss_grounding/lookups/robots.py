"""robots.txt for the live lookups (BWO, transport.opendata.ch, GeoAdmin), under RESPECT_ROBOTS.

The crawler's rules apply (`load_robots`: RFC 9309, protego). A disallowed request raises RobotsDisallowed,
an httpx.RequestError, so every lookup reports it the way it reports an unreachable source."""
import threading
import time
from urllib.parse import urlsplit

import httpx
from protego import Protego

from swiss_grounding.corpus.connectors.html import ROBOTS_USER_AGENT, load_robots

ROBOTS_MAX_AGE_SECONDS = 24 * 3600
# An unreachable robots.txt disallows the whole host (RFC 9309 2.3.1.4); ask again soon rather than a day later.
ROBOTS_RETRY_SECONDS = 300


class RobotsDisallowed(httpx.RequestError):
    """robots.txt of the host disallows the request."""


class RobotsCache:
    """Parsed robots.txt per host, shared by every lookup client of one server and safe across threads."""

    def __init__(self, user_agent: str, timeout_seconds: float, clock=time.monotonic):
        self._user_agent, self._timeout, self._clock = user_agent, timeout_seconds, clock
        self._entries: dict[str, tuple[Protego, float]] = {}
        self._lock = threading.Lock()

    def allows(self, url: str) -> bool:
        parts = urlsplit(url)
        root = f"{parts.scheme}://{parts.netloc}"
        with self._lock:
            entry = self._entries.get(root)
        if entry is None or entry[1] <= self._clock():
            with httpx.Client(timeout=self._timeout, headers={"user-agent": self._user_agent}) as http:
                parser, problem = load_robots(http, root)
            ttl = ROBOTS_RETRY_SECONDS if problem else ROBOTS_MAX_AGE_SECONDS
            entry = (parser, self._clock() + ttl)
            with self._lock:
                self._entries[root] = entry
        return entry[0].can_fetch(url, ROBOTS_USER_AGENT)


class RobotsTransport(httpx.BaseTransport):
    """Sends a request only when robots.txt of its host allows it."""

    def __init__(self, cache: RobotsCache, inner: httpx.BaseTransport | None = None):
        self._cache, self._inner = cache, inner or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if not self._cache.allows(str(request.url)):
            raise RobotsDisallowed(f"robots.txt of {request.url.host} disallows {request.url.path}", request=request)
        return self._inner.handle_request(request)

    def close(self) -> None:
        self._inner.close()


def robots_transport(cache: RobotsCache | None) -> RobotsTransport | None:
    """The transport for a lookup client: None (httpx's default) when RESPECT_ROBOTS is off."""
    return RobotsTransport(cache) if cache is not None else None
