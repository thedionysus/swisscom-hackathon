"""Compare a QueryResponse against a probe's expectation. Pure; returns failure strings."""
from collections.abc import Iterable, Mapping, Sequence
from datetime import date

from swiss_grounding.evals.probe_models import EvidenceRule, Expectation, Probe, ResolvedExpectation
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import Citation, QueryResponse

OFF_PATH = "off_path"


def _rule_label(rule: EvidenceRule) -> str:
    parts = [f"{k}={v}" for k, v in (
        ("source", rule.source), ("url_contains", rule.url_contains),
        ("extent", rule.extent), ("authority", rule.authority),
    ) if v]
    return " ".join(parts)


def _matches(rule: EvidenceRule, c: Citation, path: Sequence[str]) -> bool:
    if rule.source and c.source_id != rule.source:
        return False
    if rule.url_contains and rule.url_contains not in c.url:
        return False
    if rule.authority and c.authority != rule.authority:
        return False
    if rule.extent == OFF_PATH:
        return c.extent_id not in path
    if rule.extent and c.extent_id != rule.extent:  # noqa: SIM103
        return False
    return True


def _check_resolved(exp: ResolvedExpectation, resp: QueryResponse, tree: LocationTree) -> Iterable[str]:
    got = resp.resolved_location_id
    if exp.id is not None:
        if got != exp.id:
            yield f"resolved: expected {exp.id}, got {got}"
        return
    wanted = f"{exp.label} ({exp.level} under {exp.parent})"
    node = tree.by_id.get(got) if got else None
    if node is None:
        yield f"resolved: expected {wanted}, got {got}"
        return
    ok = (
        node.label("en") == exp.label
        and (exp.level is None or node.level.value == exp.level)
        and (exp.parent is None or node.parent_id == exp.parent)
    )
    if not ok:
        yield (f"resolved: expected {wanted}, got {got} "
               f"({node.label('en')}, {node.level.value} under {node.parent_id})")


def _check_first(exp: Expectation, citations: Sequence[Citation], today: date) -> Iterable[str]:
    wants_first = any((exp.first_extent, exp.first_authority, exp.first_url_contains, exp.first_event))
    if not wants_first:
        return
    if not citations:
        yield "first: no citations returned"
        return
    first = citations[0]
    if exp.first_extent and first.extent_id != exp.first_extent:
        yield f"first_extent: expected {exp.first_extent}, got {first.extent_id}"
    if exp.first_authority and first.authority != exp.first_authority:
        yield f"first_authority: expected {exp.first_authority}, got {first.authority}"
    if exp.first_url_contains and exp.first_url_contains not in first.url:
        yield f"first_url_contains: '{exp.first_url_contains}' not in {first.url}"
    if exp.first_event == "nearest_future":
        yield from _check_nearest_future(first, citations, today)


def _check_nearest_future(first: Citation, citations: Sequence[Citation], today: date) -> Iterable[str]:
    future = sorted(c.event_date for c in citations if c.event_date and c.event_date >= today)
    if first.event_date is None:
        yield "first_event: first citation carries no event_date"
    elif not future:
        yield f"first_event: no citation carries a future event date (nearest is {first.event_date})"
    elif first.event_date < today:
        yield f"first_event: first citation {first.event_date} is before today {today}"
    elif first.event_date != future[0]:
        yield f"first_event: expected nearest future {future[0]}, first citation has {first.event_date}"


def _coverage_counts(signal: Iterable[object]) -> dict[str, int] | None:
    """extent_id -> documents from mapping or attribute rows; None when any row is malformed."""
    counts: dict[str, int] = {}
    for row in signal:
        if isinstance(row, Mapping):
            extent, documents = row.get("extent_id"), row.get("documents")
        else:
            extent, documents = getattr(row, "extent_id", None), getattr(row, "documents", None)
        if not isinstance(extent, str) or not isinstance(documents, int):
            return None
        counts[extent] = documents
    return counts


def _check_coverage(exp: Expectation, resp: QueryResponse) -> Iterable[str]:
    if not (exp.coverage_empty or exp.coverage_present):
        return
    signal = getattr(resp, "coverage", None)
    if signal is None:
        yield "coverage: response carries no coverage signal"
        return
    counts = _coverage_counts(signal)
    if counts is None:
        yield "coverage: signal rows are not shaped {extent_id, documents}"
        return
    for extent in exp.coverage_empty:
        if extent not in counts:
            yield f"coverage: {extent} not listed in signal"
        elif counts[extent] != 0:
            yield f"coverage: expected {extent} empty, has {counts[extent]} documents"
    for extent in exp.coverage_present:
        if extent not in counts:
            yield f"coverage: {extent} not listed in signal"
        elif counts[extent] == 0:
            yield f"coverage: expected {extent} present, has 0 documents"


def _check_evidence(
    exp: Expectation, citations: Sequence[Citation], path: Sequence[str], *, skip_off_path: bool
) -> Iterable[str]:
    for rule in exp.must_include:
        if skip_off_path and rule.extent == OFF_PATH:
            continue
        if not any(_matches(rule, c, path) for c in citations):
            yield f"must_include: no citation matched {_rule_label(rule)}"
    for rule in exp.must_exclude:
        if skip_off_path and rule.extent == OFF_PATH:
            continue
        for c in citations:
            if _matches(rule, c, path):
                yield f"must_exclude: citation matched {_rule_label(rule)} ({c.url})"


def check(probe: Probe, resp: QueryResponse, tree: LocationTree, today: date) -> tuple[str, ...]:
    """Every way the response falls short of the probe's expectation; empty means pass.

    The caller decides what `today` is; pass the probe's as_of when it has one.
    """
    exp = probe.expect
    failures: list[str] = []
    if resp.status != exp.status:
        failures.append(f"status: expected {exp.status}, got {resp.status}")
    if exp.resolved is not None:
        failures.extend(_check_resolved(exp.resolved, resp, tree))
    if exp.method and resp.resolution_method != exp.method:
        failures.append(f"method: expected {exp.method}, got {resp.resolution_method}")
    for alt in exp.alternatives_include:
        if alt not in resp.alternatives:
            if resp.alternatives:
                failures.append(f"alternatives: {alt} missing from {', '.join(resp.alternatives)}")
            else:
                failures.append(f"alternatives: {alt} missing; none returned")
    resolved = resp.resolved_location_id
    resolved_known = resolved in tree.by_id
    path = tree.path(resolved) if resolved_known else ()
    uses_off_path = any(
        rule.extent == OFF_PATH for rule in (*exp.must_include, *exp.must_exclude)
    )
    if not resolved_known and uses_off_path:
        failures.append("off_path: response resolved no location, so no extent path to judge against")
    failures.extend(_check_evidence(exp, resp.citations, path, skip_off_path=not resolved_known))
    failures.extend(_check_first(exp, resp.citations, today))
    failures.extend(_check_coverage(exp, resp))
    if exp.message_contains and exp.message_contains not in resp.message:
        failures.append(f"message: '{exp.message_contains}' not in \"{resp.message}\"")
    return tuple(failures)
