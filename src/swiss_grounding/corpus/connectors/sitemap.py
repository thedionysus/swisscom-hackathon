"""Sitemap seeding for the HTML crawler (A11).

Reads sitemap files and sitemap indexes (plain or gzip, whatever content-type the server labels
them with -- ch.ch serves its sitemap as text/html) and returns page URLs that pass the caller's
filter, stopping as soon as `limit` URLs are found so large indexes are never walked in full.
"""
import gzip
import re
import zlib
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from io import BytesIO

import httpx
from bs4 import BeautifulSoup

MAX_SITEMAP_BYTES = 50_000_000
MAX_SITEMAP_FILES = 200


@dataclass(frozen=True)
class SitemapSeeds:
    urls: tuple[str, ...]
    errors: tuple[tuple[str, str], ...]


class _Unreadable(Exception):
    pass


def _decompress(body: bytes) -> bytes:
    if not body.startswith(b"\x1f\x8b"):
        return body
    try:
        with gzip.GzipFile(fileobj=BytesIO(body)) as handle:
            data = handle.read(MAX_SITEMAP_BYTES + 1)
    except (OSError, EOFError, zlib.error) as exc:
        raise _Unreadable(f"sitemap is not valid gzip: {exc}") from exc
    if len(data) > MAX_SITEMAP_BYTES:
        raise _Unreadable(f"sitemap larger than {MAX_SITEMAP_BYTES} bytes")
    return data


def _entries(body: bytes) -> tuple[list[str], list[str]]:
    """(child sitemap URLs, page URLs). Only <loc> directly under <sitemap> or <url> counts, so
    image:loc / video:loc entries of image and video sitemaps are ignored."""
    soup = BeautifulSoup(body, "xml")
    children, pages = [], []
    for loc in soup.find_all("loc"):
        parent = loc.parent.name if loc.parent else None
        text = loc.get_text(strip=True)
        if not text or loc.prefix:
            continue
        if parent == "sitemap":
            children.append(text)
        elif parent == "url":
            pages.append(text)
    return children, pages


def collect_sitemap_urls(http: httpx.Client, sitemap_urls: Sequence[str], include: Sequence[str], limit: int,
                         accept: Callable[[str], bool], fetchable: Callable[[str], bool],
                         pause: Callable[[], None]) -> SitemapSeeds:
    """Page URLs from `sitemap_urls` matching any `include` regex (all when empty) and `accept`.

    `fetchable` gates each sitemap request (robots.txt); `pause` runs after each request.
    Unreadable sitemaps become errors; the crawl continues without them.
    """
    patterns = [re.compile(p) for p in include]
    queue = deque(sitemap_urls)
    visited: set[str] = set()
    found: dict[str, None] = {}
    errors: list[tuple[str, str]] = []
    while queue and len(found) < limit and len(visited) < MAX_SITEMAP_FILES:
        sitemap = queue.popleft()
        if sitemap in visited:
            continue
        visited.add(sitemap)
        if not fetchable(sitemap):
            errors.append((sitemap, "sitemap disallowed by robots.txt"))
            continue
        try:
            response = http.get(sitemap, follow_redirects=True, timeout=60)
        except httpx.HTTPError as exc:
            errors.append((sitemap, f"sitemap fetch failed: {exc}"))
            continue
        finally:
            pause()
        if response.status_code >= 400:
            errors.append((sitemap, f"sitemap HTTP {response.status_code}"))
            continue
        try:
            children, pages = _entries(_decompress(response.content))
        except _Unreadable as exc:
            errors.append((sitemap, str(exc)))
            continue
        queue.extend(children)
        for url in pages:
            if url not in found and (not patterns or any(p.search(url) for p in patterns)) and accept(url):
                found[url] = None
                if len(found) >= limit:
                    break
    return SitemapSeeds(urls=tuple(found), errors=tuple(errors))
