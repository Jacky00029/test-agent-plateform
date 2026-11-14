"""Token bucket rate limiter for agent tool calls."""
import math
import time
from typing import Any, Callable, Optional


Number = (int, float)


class RateLimiterError(ValueError):
    """Raised for invalid rate limiter configuration or input."""


def _positive_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Number):
        raise RateLimiterError(name + ' must be a number')
    if not math.isfinite(value):
        raise RateLimiterError(name + ' must be finite')
    if value <= 0:
        raise RateLimiterError(name + ' must be greater than 0')
    return float(value)


class TokenBucket:
    """Allow bursts up to ``capacity`` and refill at ``refill_per_second``.

    Tokens refill lazily whenever the bucket is observed. ``try_acquire``
    returns ``False`` without consuming tokens when the request cannot be
    satisfied. ``retry_after`` reports how long to wait for the requested
    tokens and never consumes any.
    """

    def __init__(self, capacity: float, refill_per_second: float,
                 clock: Optional[Callable[[], float]] = None):
        self._capacity = _positive_number(capacity, 'capacity')
        self._rate = _positive_number(refill_per_second, 'refill_per_second')
        if clock is not None and not callable(clock):
            raise RateLimiterError('clock must be callable')
        self._clock = clock or time.monotonic
        self._tokens = self._capacity
        self._updated = self._clock()

    @property
    def capacity(self) -> float:
        return self._capacity

    @property
    def refill_per_second(self) -> float:
        return self._rate

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._updated
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._updated = now

    @property
    def tokens(self) -> float:
        """Current token count after applying elapsed refill."""
        self._refill()
        return self._tokens

    def try_acquire(self, tokens: float = 1) -> bool:
        """Consume ``tokens`` when available; leave the bucket untouched otherwise."""
        amount = _positive_number(tokens, 'tokens')
        self._refill()
        if amount > self._tokens:
            return False
        self._tokens -= amount
        return True

    def retry_after(self, tokens: float = 1) -> float:
        """Seconds until ``tokens`` are available; 0 when already available.

        Requests above ``capacity`` can never be satisfied and return
        ``float('inf')``.
        """
        amount = _positive_number(tokens, 'tokens')
        self._refill()
        if amount <= self._tokens:
            return 0.0
        if amount > self._capacity:
            return float('inf')
        return (amount - self._tokens) / self._rate
