"""Which `as_of` dates this index can answer for, and how it refuses the rest (D2).

Ingestion fetches the version of an act that is in force *now* and nothing else, so the
index holds current consolidations with no version history behind them. `valid_from`
records when the one indexed version entered into force. There is no earlier version to
fall back to, which means `as_of` can only ever subtract from what is retrievable; it
can never reach back.

A date before the oldest indexed `valid_from` therefore reaches nothing. It is not a
narrow question, it is an unanswerable one, and the old behaviour answered it anyway:
every act was filtered out and the undated pages that bypassed the filter came back as
the answer to a question about what the law said years ago. Refusing is strictly more
useful than that, and more useful than an empty result, because the refusal carries the
one fact the caller needs to recover -- the earliest date the index *can* answer for.

Two refusals, deliberately distinct, because they call for different repairs:

- **Too early.** The index has dated documents, just none reaching back that far. The
  caller moves the date forward to the named boundary, or drops it.
- **Nothing is dated at all.** No indexed document records a validity date, so no date
  is answerable and there is no boundary to name. The only repair is to drop `as_of`.

The boundary itself is inclusive: a version that entered into force on a date *was* in
force on that date, so refusing the boundary would refuse a question the index answers.

Kept pure and separate from the query that finds the boundary (`search.
earliest_indexed_version`) so the wording and the discrimination can be tested without a
database, and so the one thing that needs the index is a single value passed in.
"""

from datetime import date

# Both name the date that was asked for, because it is usually the caller's own typo or
# an off-by-a-decade default, and a refusal that does not quote it back is a guess.
TOO_EARLY = (
    "as_of {as_of} is earlier than {earliest}, the earliest date this index can answer "
    "for. Only current consolidations are indexed and there is no version history, so "
    "the index cannot say what was in force before {earliest}. Search again with a date "
    "on or after {earliest}, or without as_of for what is in force now."
)

NOTHING_DATED = (
    "as_of {as_of} cannot be answered: no indexed document records a validity date, so "
    "the index cannot say what was in force on any date. Search again without as_of for "
    "what is in force now."
)


def as_of_rejection(as_of: date | None, earliest: date | None) -> str | None:
    """The message refusing `as_of`, or None when the index can answer for it.

    `earliest` is what `search.earliest_indexed_version` returned: the oldest `valid_from`
    retrieval can reach, or None when no indexed document records one at all.
    """
    if as_of is None:
        return None
    if earliest is None:
        return NOTHING_DATED.format(as_of=as_of)
    if as_of < earliest:
        return TOO_EARLY.format(as_of=as_of, earliest=earliest)
    return None
