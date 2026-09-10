import httpx

from swiss_grounding.config import Settings
from swiss_grounding.ingest.fetchers.api import ApiFetcher
from swiss_grounding.ingest.fetchers.base import Fetcher
from swiss_grounding.ingest.fetchers.fedlex import FedlexFetcher
from swiss_grounding.ingest.fetchers.html_crawl import CrawlLimits, HtmlCrawlFetcher
from swiss_grounding.ingest.fetchers.pdf import PdfFetcher
from swiss_grounding.registry.models import FetchStrategy


def _http(settings: Settings) -> httpx.Client:
    return httpx.Client(timeout=settings.fetch_timeout_seconds, headers={"user-agent": settings.user_agent})


def build_fetcher(strategy: FetchStrategy, settings: Settings) -> Fetcher:
    http = _http(settings)
    if strategy == FetchStrategy.HTML_CRAWL:
        return HtmlCrawlFetcher(http=http, limits=CrawlLimits(
            max_pages=settings.crawl_max_pages, delay_seconds=settings.crawl_delay_seconds))
    if strategy == FetchStrategy.PDF:
        return PdfFetcher(http=http)
    if strategy == FetchStrategy.API:
        return ApiFetcher(http=http)
    if strategy == FetchStrategy.FEDLEX_SPARQL:
        return FedlexFetcher(http=http)
    raise ValueError(f"unsupported fetch strategy: {strategy}")
