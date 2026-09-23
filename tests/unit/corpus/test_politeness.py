import itertools
import threading
import time

from swiss_grounding.corpus.connectors.politeness import HostThrottle


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
