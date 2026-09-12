import httpx

from swiss_grounding.config import Settings
from swiss_grounding.ingest.fetchers.api import ApiFetcher
from swiss_grounding.ingest.fetchers.base import Fetcher
from swiss_grounding.ingest.fetchers.fedlex import FedlexFetcher
from swiss_grounding.ingest.fetchers.html_crawl import CrawlLimits, HtmlCrawlFetcher
from swiss_grounding.ingest.fetchers.pdf import PdfFetcher
from swiss_grounding.ingest.fetchers.retry import RetryPolicy
from swiss_grounding.registry.models import FetchStrategy


def _http(settings: Settings) -> httpx.Client:
    # Transport-level retries cover connection failures; HTTP-level retries live in the fetchers.
    transport = httpx.HTTPTransport(retries=settings.fetch_retry_attempts - 1)
    return httpx.Client(timeout=settings.fetch_timeout_seconds, headers={"user-agent": settings.user_agent},
                        transport=transport)


def _retry_policy(settings: Settings) -> RetryPolicy:
    return RetryPolicy(attempts=settings.fetch_retry_attempts, backoff_seconds=settings.fetch_retry_backoff_seconds)


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
        return FedlexFetcher(http=http, retry=_retry_policy(settings))
    raise ValueError(f"unsupported fetch strategy: {strategy}")
