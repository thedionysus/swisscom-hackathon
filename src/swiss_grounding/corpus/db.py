from importlib import resources

from swiss_grounding.db.connection import connect


def corpus_schema_sql() -> str:
    return resources.files("swiss_grounding.corpus").joinpath("schema.sql").read_text()


def apply_corpus_schema(database_url: str) -> None:
    """Create or bring up to date the corpus schema. Needs `public.location` to exist."""
    with connect(database_url) as conn:
        conn.execute(corpus_schema_sql())
