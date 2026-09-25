from importlib import resources

from swiss_grounding.db.connection import connect


def serving_schema_sql() -> str:
    return resources.files("swiss_grounding.serving").joinpath("schema.sql").read_text()


def apply_serving_schema(database_url: str) -> None:
    """Create or bring up to date the serving schema. Idempotent."""
    with connect(database_url) as conn:
        conn.execute(serving_schema_sql())
