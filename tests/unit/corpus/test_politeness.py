import itertools
import threading
import time

import httpx

from swiss_grounding.corpus.connectors.politeness import (
    DEFAULT_RETRY_SECONDS,
    MAX_HOST_DELAY_SECONDS,
    MAX_RETRY_SECONDS,
    FetchResult,
    HostThrottle,
    parse_retry_after,
    request_with_backoff,
)


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_second_request_to_a_host_waits_out_the_delay():
    clock = FakeClock()
    throttle = HostThrottle(clock=clock)
    throttle.wait("https://a.ch/1", 1.0, clock.sleep)
    clock.now += 0.25
    throttle.wait("https://a.ch/2", 1.0, clock.sleep)
    assert clock.sleeps == [0.75]


def test_other_hosts_and_zero_delay_do_not_wait():
    clock = FakeClock()
    throttle = HostThrottle(clock=clock)
    throttle.wait("https://a.ch/1", 1.0, clock.sleep)
    throttle.wait("https://b.ch/1", 1.0, clock.sleep)
    throttle.wait("https://a.ch/2", 0, clock.sleep)
    assert clock.sleeps == []


def test_threads_sharing_a_host_are_spaced_by_the_delay():
    throttle = HostThrottle()
    starts: list[float] = []
    lock = threading.Lock()

    def worker():
        throttle.wait("https://a.ch/x", 0.15, time.sleep)
        with lock:
            starts.append(time.monotonic())

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    starts.sort()
    assert all(b - a >= 0.14 for a, b in itertools.pairwise(starts))


# --- Retry-After parsing -----------------------------------------------------------------------

def test_retry_after_numeric_seconds_is_used_as_is():
    assert parse_retry_after("2") == 2.0


def test_retry_after_missing_defaults():
    assert parse_retry_after(None) == DEFAULT_RETRY_SECONDS
    assert parse_retry_after("") == DEFAULT_RETRY_SECONDS


def test_retry_after_unparseable_defaults():
    assert parse_retry_after("not a date or a number") == DEFAULT_RETRY_SECONDS


def test_retry_after_is_capped():
    assert parse_retry_after("99999") == MAX_RETRY_SECONDS


def test_retry_after_http_date_is_converted_to_seconds_from_now():
    from datetime import UTC, datetime, timedelta

    when = datetime.now(UTC) + timedelta(seconds=5)
    header = when.strftime("%a, %d %b %Y %H:%M:%S GMT")
    seconds = parse_retry_after(header)
    assert 3.0 <= seconds <= 6.0


# --- HostThrottle.backoff -----------------------------------------------------------------------

def test_backoff_sleeps_retry_after_then_raises_the_host_delay():
    clock = FakeClock()
    throttle = HostThrottle(clock=clock)
    throttle.wait("https://a.ch/1", 1.0, clock.sleep)   # establishes the host's last-used delay
    throttle.backoff("https://a.ch/1", 2.0, clock.sleep)
    assert 2.0 in clock.sleeps
    # The raised delay is enforced as a floor on the next wait(), even with a smaller delay passed.
    before = len(clock.sleeps)
    throttle.wait("https://a.ch/1", 0.1, clock.sleep)
    assert len(clock.sleeps) > before


def test_backoff_caps_the_raised_delay():
    clock = FakeClock()
    throttle = HostThrottle(clock=clock)
    throttle.wait("https://a.ch/1", 20.0, clock.sleep)
    throttle.backoff("https://a.ch/1", 1.0, clock.sleep)
    throttle.backoff("https://a.ch/1", 1.0, clock.sleep)
    assert throttle._min_delay["a.ch"] == MAX_HOST_DELAY_SECONDS


# --- request_with_backoff -----------------------------------------------------------------------

def test_429_with_retry_after_then_200_is_returned_and_host_delay_raised():
    clock = FakeClock()
    throttle = HostThrottle(clock=clock)
    responses = iter([FetchResult(429, httpx.Headers({"retry-after": "2"})), FetchResult(200, httpx.Headers())])
    before_calls: list[str] = []
    result = request_with_backoff("https://a.ch/x", throttle, before_calls.append, lambda: next(responses),
                                  clock.sleep)
    assert result.status_code == 200
    assert 2.0 in clock.sleeps
    assert before_calls == ["https://a.ch/x", "https://a.ch/x"]
    assert throttle._min_delay.get("a.ch", 0.0) > 0


def test_three_429s_return_the_last_failing_response_without_a_fourth_attempt():
    clock = FakeClock()
    throttle = HostThrottle(clock=clock)
    calls = {"n": 0}

    def send():
        calls["n"] += 1
        return FetchResult(429, httpx.Headers({"retry-after": "1"}))

    result = request_with_backoff("https://a.ch/x", throttle, lambda u: None, send, clock.sleep)
    assert result.status_code == 429
    assert calls["n"] == 3
