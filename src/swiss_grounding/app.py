"""Composition root: builds fully wired objects from settings."""
from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.locations.geoadmin import GeoAdminClient
from swiss_grounding.locations.repository import load_tree
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.retrieval.embedder import build_embedder
from swiss_grounding.retrieval.query_core import QueryCore
from swiss_grounding.retrieval.rerank import RerankWeights


def build_query_core(settings: Settings) -> QueryCore:
    with connect(settings.database_url) as conn:
        tree = load_tree(conn)
    if not tree.by_id:
        raise RuntimeError("location table is empty; run `swiss-grounding db seed` first")
    geo = GeoAdminClient.from_settings(settings.geoadmin_base_url, settings.geoadmin_timeout_seconds)
    embedder = build_embedder(settings.embedding_backend, settings.embedding_model, settings.embedding_dim)
    return QueryCore(
        database_url=settings.database_url, tree=tree,
        resolver=LocationResolver(tree, geo), embedder=embedder, weights=RerankWeights(),
    )
