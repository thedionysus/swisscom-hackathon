import re

EVENT_DATE_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}$")


def calendar_series(identifier: str | None) -> str | None:
    """The calendar series a document identifier belongs to.

    Calendar records repeat one series across many dates: `cardboard-2026-09-10` and
    `cardboard-2026-09-24` are both the `cardboard` series, just different collection dates.
    Strips a trailing `-YYYY-MM-DD` from the identifier to recover the series; an identifier
    with no such suffix is its own series unchanged. Returns None for a falsy identifier.
    """
    if not identifier:
        return None
    return EVENT_DATE_SUFFIX.sub("", identifier)
