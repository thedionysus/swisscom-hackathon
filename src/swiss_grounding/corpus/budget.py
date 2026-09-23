import psycopg

# USD per 1M tokens on the Batch API: (input, output). Verify on the day of the run.
PRICES: dict[str, tuple[float, float]] = {
    "text-embedding-3-large": (0.065, 0.0),
    "gpt-5-mini": (0.125, 1.0),
    "gpt-5-nano": (0.025, 0.2),
    # Anthropic sync fallback, stated at half its list price like the rows above (sync x2 = $1 / $5).
    "claude-haiku-4-5-20251001": (0.5, 2.5),
    "claude-haiku-4-5": (0.5, 2.5),
}
SYNC_MULTIPLIER = 2.0
CHARS_PER_TOKEN = 3          # conservative for German/French/Italian
OCR_IMAGE_TOKENS = 1500      # per page image; replaced by the pilot's measured value (Task 16)

# corpus.batch_job.kind values that map to the "describe" ledger kind (A3).
DESCRIBE_BATCH_KINDS = ("describe-doc", "describe-chunk")
# Batch statuses that no longer count against the budget while in flight.
TERMINAL_NON_COUNTING_STATUSES = ("failed", "expired", "cancelled")


class BudgetExceeded(RuntimeError):
    pass


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def cost_usd(model: str, input_tokens: int, output_tokens: int, batch: bool = True) -> float:
    price_in, price_out = PRICES[model]
    usd = (input_tokens * price_in + output_tokens * price_out) / 1_000_000
    return usd if batch else usd * SYNC_MULTIPLIER


def record_spend(conn: psycopg.Connection, *, kind: str, model: str, usd: float, input_tokens: int,
                 output_tokens: int, estimated: bool) -> None:
    conn.execute("insert into corpus.llm_spend (kind, model, usd, input_tokens, output_tokens, estimated) "
                 "values (%s,%s,%s,%s,%s,%s)", (kind, model, usd, input_tokens, output_tokens, estimated))


def spent(conn: psycopg.Connection, kind: str | None = None) -> float:
    row = conn.execute("select coalesce(sum(usd), 0) as usd from corpus.llm_spend where %s::text is null or kind = %s",
                       (kind, kind)).fetchone()
    return float(row["usd"])


def _in_flight_batch_usd(conn: psycopg.Connection, kind: str | None = None) -> float:
    """A3: batch jobs not yet ingested still count against the cap, so a second run of the
    pipeline cannot pass `ensure_within` while the first run's batches are still pending."""
    placeholders = ",".join(["%s"] * len(TERMINAL_NON_COUNTING_STATUSES))
    params: list[object] = list(TERMINAL_NON_COUNTING_STATUSES)
    kind_clause = ""
    if kind is not None:
        if kind == "describe":
            batch_kinds = DESCRIBE_BATCH_KINDS
        else:
            batch_kinds = (kind,)
        kind_placeholders = ",".join(["%s"] * len(batch_kinds))
        kind_clause = f" and kind in ({kind_placeholders})"
        params.extend(batch_kinds)
    row = conn.execute(
        f"select coalesce(sum(estimated_usd), 0) as usd from corpus.batch_job "
        f"where ingested_at is null and status not in ({placeholders}){kind_clause}",
        params,
    ).fetchone()
    return float(row["usd"])


def ensure_within(conn: psycopg.Connection, *, estimate: float, total_cap: float,
                  kind: str | None = None, kind_cap: float | None = None) -> None:
    total = spent(conn) + _in_flight_batch_usd(conn)
    if total + estimate > total_cap:
        raise BudgetExceeded(f"total budget: spent ${total:.2f} + estimate ${estimate:.2f} > cap ${total_cap:.2f}")
    if kind and kind_cap is not None:
        part = spent(conn, kind) + _in_flight_batch_usd(conn, kind)
        if part + estimate > kind_cap:
            raise BudgetExceeded(f"{kind} budget: spent ${part:.2f} + estimate ${estimate:.2f} > cap ${kind_cap:.2f}")


def remaining_budget(conn: psycopg.Connection, *, total_cap: float, kind: str | None = None,
                     kind_cap: float | None = None) -> float:
    """Headroom left for a new estimate: the total cap's, and the kind sub-cap's when one applies (the
    smaller of the two, same as `ensure_within` checking both)."""
    remaining = total_cap - spent(conn) - _in_flight_batch_usd(conn)
    if kind and kind_cap is not None:
        kind_remaining = kind_cap - spent(conn, kind) - _in_flight_batch_usd(conn, kind)
        remaining = min(remaining, kind_remaining)
    return remaining


def tasks_that_fit(remaining_usd: float, estimate_usd: float, num_tasks: int) -> int:
    """How many of `num_tasks` fit in `remaining_usd`, at the same average per-task price that produced
    `estimate_usd` for all of them. Never negative, never more than `num_tasks`."""
    if num_tasks <= 0 or estimate_usd <= 0 or remaining_usd <= 0:
        return 0
    per_task = estimate_usd / num_tasks
    return max(0, min(num_tasks, int(remaining_usd // per_task)))
