from importlib import resources

from swiss_grounding.db.connection import connect


def render_schema(embedding_dim: int) -> str:
    sql = resources.files("swiss_grounding.db").joinpath("schema.sql").read_text()
    return sql.replace("{{EMBEDDING_DIM}}", str(embedding_dim))


def apply_schema(database_url: str, embedding_dim: int) -> None:
    with connect(database_url) as conn:
        conn.execute(render_schema(embedding_dim))
