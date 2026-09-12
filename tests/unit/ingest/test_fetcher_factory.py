import pytest

from swiss_grounding.config import Settings
from swiss_grounding.ingest.fetchers import build_fetcher
from swiss_grounding.ingest.fetchers.api import ApiFetcher
from swiss_grounding.ingest.fetchers.fedlex import FedlexFetcher
from swiss_grounding.ingest.fetchers.html_crawl import HtmlCrawlFetcher
from swiss_grounding.ingest.fetchers.pdf import PdfFetcher
from swiss_grounding.ingest.fetchers.retry import RetryPolicy
from swiss_grounding.registry.models import FetchStrategy


@pytest.mark.parametrize("strategy,cls", [
    (FetchStrategy.HTML_CRAWL, HtmlCrawlFetcher), (FetchStrategy.PDF, PdfFetcher),
    (FetchStrategy.API, ApiFetcher), (FetchStrategy.FEDLEX_SPARQL, FedlexFetcher),
])
def test_build_fetcher(strategy, cls):
    settings = Settings(database_url="postgresql://u:p@h/db", crawl_delay_seconds=0)
    assert isinstance(build_fetcher(strategy, settings), cls)


def test_build_fetcher_rejects_unknown():
    settings = Settings(database_url="postgresql://u:p@h/db")
    with pytest.raises(ValueError, match="unsupported"):
        build_fetcher("carrier_pigeon", settings)  # type: ignore[arg-type]


def test_fedlex_fetcher_gets_retry_policy_from_settings():
    settings = Settings(database_url="postgresql://u:p@h/db", fetch_retry_attempts=5, fetch_retry_backoff_seconds=0.1)
    fetcher = build_fetcher(FetchStrategy.FEDLEX_SPARQL, settings)
    assert fetcher.retry == RetryPolicy(attempts=5, backoff_seconds=0.1)
