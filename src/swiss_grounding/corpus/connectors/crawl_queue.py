"""The HTML crawler's frontier: new-first, with known pages re-checked last.

Two queues. The frontier holds start URLs, sitemap seeds and every link discovered this run;
its pages are fetched in full. The revisit queue holds already-known pages nothing reachable
this run has linked to; only those are fetched conditionally (If-None-Match/-Modified-Since),
since a 304 hides a page's links. A known URL that turns up as a link is promoted to the
frontier, and its stale revisit entry is dropped.
"""
from collections import deque
from collections.abc import Iterable


class CrawlQueue:
    def __init__(self, start_urls: Iterable[str], known_urls: Iterable[str]):
        self._frontier = deque(start_urls)
        starts = set(self._frontier)
        self._revisit_order = deque(u for u in known_urls if u not in starts)
        self._revisit = set(self._revisit_order)
        self._queued = starts | self._revisit
        self.seen: set[str] = set()

    def is_known_or_queued(self, url: str) -> bool:
        return url in self._queued or url in self.seen

    def add(self, url: str, front: bool = False) -> None:
        """Queue a URL for a full fetch. `front` pulls it ahead of everything already queued,
        even if it is queued further back (the stale entry is skipped as seen later)."""
        if url in self.seen:
            return
        if url in self._revisit:
            self._revisit.discard(url)
        elif url in self._queued and not front:
            return
        if front:
            self._frontier.appendleft(url)
        else:
            self._frontier.append(url)
        self._queued.add(url)

    def pop(self) -> tuple[str, bool] | None:
        """(url, conditional) for the next page to fetch, or None when both queues are empty."""
        if self._frontier:
            return self._frontier.popleft(), False
        while self._revisit_order:
            url = self._revisit_order.popleft()
            if url in self._revisit:
                self._revisit.discard(url)
                return url, True
        return None
