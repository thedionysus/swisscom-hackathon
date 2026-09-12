import time
from collections.abc import Callable
from dataclasses import dataclass

Sleep = Callable[[float], None]

DEFAULT_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 0.5


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry: at most `attempts` tries, sleeping `backoff_seconds * try_number` between them."""
    attempts: int = DEFAULT_ATTEMPTS
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("RetryPolicy.attempts must be at least 1")
        if self.backoff_seconds < 0:
            raise ValueError("RetryPolicy.backoff_seconds must not be negative")


DEFAULT_RETRY_POLICY = RetryPolicy()


def retry[T](
    operation: Callable[[], T],
    *,
    policy: RetryPolicy,
    retry_on: tuple[type[BaseException], ...],
    retry_if: Callable[[T], bool] = lambda _: False,
    sleep: Sleep = time.sleep,
) -> T:
    """Call `operation` up to `policy.attempts` times.

    Retries when it raises one of `retry_on` or when `retry_if(result)` is true.
    The last exception is re-raised; the last unwanted result is returned so the
    caller can report it with its own reason.
    """
    for attempt in range(1, policy.attempts + 1):
        is_last = attempt == policy.attempts
        try:
            result = operation()
        except retry_on:
            if is_last:
                raise
        else:
            if is_last or not retry_if(result):
                return result
        if policy.backoff_seconds:
            sleep(policy.backoff_seconds * attempt)
    raise AssertionError("unreachable")  # pragma: no cover
