"""Composition root: builds fully wired objects from settings."""
import logging
from collections.abc import Callable
from datetime import date
from pathlib import Path

from swiss_grounding.config import Settings
from swiss_grounding.corpus.providers import FakeEmbeddings, LocalBgeM3, OpenAIEmbeddings
from swiss_grounding.db.connection import connect
from swiss_grounding.locations.geoadmin import GeoAdminClient
from swiss_grounding.locations.repository import load_tree
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.lookups.robots import RobotsCache, robots_transport
from swiss_grounding.retrieval.embedder import build_embedder
from swiss_grounding.retrieval.query_core import QueryCore
from swiss_grounding.retrieval.rerank import RerankWeights
from swiss_grounding.serving.relevance import load_relevance
from swiss_grounding.serving.reranker import (
    CrossEncoderReranker,
    OverlapReranker,
    Reranker,
    choose_model,
    detect_device,
)
from swiss_grounding.serving.scope import load_scope
from swiss_grounding.serving.search_service import SearchService, query_embedder
from swiss_grounding.serving.translation import NoTranslator, SupertextTranslator, Translator

FAKE_QUERY_DIM = 1024  # the corpus tables are vector(1024) even in tests
log = logging.getLogger(__name__)


def load_location_tree(conn) -> LocationTree:
    tree = load_tree(conn)
    if not tree.by_id:
        raise RuntimeError("location table is empty; run `swiss-grounding db seed` first")
    return tree


def build_query_core(settings: Settings, today: Callable[[], date] = date.today) -> QueryCore:
    """today is the clock the reranker uses to tell past calendar events from upcoming ones."""
    with connect(settings.database_url) as conn:
        tree = load_location_tree(conn)
    geo = GeoAdminClient.from_settings(settings.geoadmin_base_url, settings.geoadmin_timeout_seconds)
    embedder = build_embedder(settings.embedding_backend, settings.embedding_model, settings.embedding_dim)
    return QueryCore(
        database_url=settings.database_url, tree=tree,
        resolver=LocationResolver(tree, geo), embedder=embedder, weights=RerankWeights(),
        today=today,
    )


def build_query_provider(settings: Settings):
    if settings.query_embedder == "fake":
        return FakeEmbeddings(FAKE_QUERY_DIM)
    if settings.serving_index == "openai-3l":
        return OpenAIEmbeddings(settings.openai_api_key)
    return LocalBgeM3()


def build_reranker(settings: Settings, device: str) -> Reranker:
    if settings.reranker_model == "overlap":
        return OverlapReranker()
    model = choose_model(settings.reranker_model, gpu_model=settings.reranker_gpu_model,
                         cpu_model=settings.reranker_cpu_model, device=device)
    tokens = settings.reranker_max_tokens_cpu if device == "cpu" else settings.reranker_max_tokens
    return CrossEncoderReranker(model, device=device, max_tokens=tokens)


def relevance_path(settings: Settings, reranker_name: str) -> Path:
    """One fitted model per reranker: the reranker depends on the hardware."""
    slug = reranker_name.replace("/", "__")
    return Path(settings.relevance_model_path).with_suffix(f".{slug}.json")


def build_translator(settings: Settings) -> Translator:
    """TRANSLATOR picks the service; supertext without a key, or none, translates nothing."""
    if settings.translator == "none":
        return NoTranslator()
    if settings.translator == "apertus":
        from swiss_grounding.corpus.llm_factory import apertus_llm
        from swiss_grounding.serving.translation_apertus import ApertusTranslator
        # One retry: the 5 requests/s limit resets within about a second.
        return ApertusTranslator(apertus_llm(settings, timeout_seconds=settings.apertus_translate_timeout_seconds,
                                             max_retries=1))
    if not settings.supertext_api_key:
        log.info("SUPERTEXT_API_KEY not set: questions and cited passages are not translated")
        return NoTranslator()
    return SupertextTranslator(settings.supertext_api_key, base_url=settings.supertext_base_url,
                               timeout_seconds=settings.supertext_timeout_seconds)


def build_search_service(settings: Settings, today: Callable[[], date] = date.today) -> SearchService:
    with connect(settings.database_url) as conn:
        tree = load_location_tree(conn)
        scope = load_scope(conn, tree)
    if settings.query_embedder == "fake":
        log.warning("QUERY_EMBEDDER=fake: query vectors are meaningless; use only in tests")
    device = "cpu" if settings.reranker_model == "overlap" else detect_device()
    robots = RobotsCache(settings.corpus_user_agent, settings.geoadmin_timeout_seconds) if settings.respect_robots else None
    geo = GeoAdminClient.from_settings(settings.geoadmin_base_url, settings.geoadmin_timeout_seconds,
                                       transport=robots_transport(robots))
    reranker = build_reranker(settings, device)
    candidates = settings.rerank_candidates_cpu if device == "cpu" else settings.rerank_candidates
    return SearchService(
        database_url=settings.database_url, tree=tree, resolver=LocationResolver(tree, geo),
        embed=query_embedder(build_query_provider(settings)), reranker=reranker,
        relevance=load_relevance(relevance_path(settings, reranker.name), reranker.name),
        index=settings.serving_index, rerank_candidates=candidates, local_quota=settings.local_candidate_quota,
        ef_search=settings.hnsw_ef_search, today=today, translator=build_translator(settings),
        query_langs=settings.translate_query_languages, translate_citations=settings.translate_citations,
        scope=scope)
