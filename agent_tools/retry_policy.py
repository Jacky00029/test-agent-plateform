"""Deterministic exponential backoff with optional jitter and typed retries."""
import random
import time
from typing import Any, Callable, Optional, Sequence, Tuple, Type


Number = (int, float)


class RetryPolicyError(ValueError):
    """Raised for invalid retry policy configuration."""


class RetryPolicy:
    """Retry a callable with exponential backoff.

    ``max_attempts`` is the total number of calls, including the first one.
    ``delays`` therefore contains ``max_attempts - 1`` values: ``base_delay``,
    then doubling values capped at ``max_delay``. ``run`` retries only the
    exception types in ``retry_on`` and re-raises the final exception once the
    attempts are exhausted.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 5.0,
        jitter: float = 0.0,
        retry_on: Any = (Exception,),
        sleep: Optional[Callable[[float], Any]] = None,
        rng: Optional[random.Random] = None,
    ):
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
            raise RetryPolicyError('max_attempts must be an integer')
        if max_attempts < 1:
            raise RetryPolicyError('max_attempts must be at least 1')
        if isinstance(base_delay, bool) or not isinstance(base_delay, Number):
            raise RetryPolicyError('base_delay must be a number')
        if base_delay < 0:
            raise RetryPolicyError('base_delay must not be negative')
        if isinstance(max_delay, bool) or not isinstance(max_delay, Number):
            raise RetryPolicyError('max_delay must be a number')
        if max_delay < 0:
            raise RetryPolicyError('max_delay must not be negative')
        if isinstance(jitter, bool) or not isinstance(jitter, Number):
            raise RetryPolicyError('jitter must be a number')
        if not 0 <= jitter <= 1:
            raise RetryPolicyError('jitter must be between 0 and 1')

        self.max_attempts = max_attempts
        self.base_delay = float(base_delay)
        self.max_delay = float(max_delay)
        self.jitter = float(jitter)
        self.retry_on = self._normalize_exceptions(retry_on)
        self._sleep = sleep or time.sleep
        self._rng = rng or random.Random()

    @staticmethod
    def _normalize_exceptions(value: Any) -> Tuple[Type[BaseException], ...]:
        if isinstance(value, type) and issubclass(value, BaseException):
            return (value,)
        if isinstance(value, (tuple, list)) and value and all(
            isinstance(item, type) and issubclass(item, BaseException) for item in value
        ):
            return tuple(value)
        raise RetryPolicyError('retry_on must be an exception type or a non-empty tuple of types')

    @property
    def delays(self) -> Tuple[float, ...]:
        """Delays before each retry; length is ``max_attempts - 1``."""
        result = []
        delay = self.base_delay
        for _ in range(self.max_attempts - 1):
            delay = min(delay, self.max_delay)
            result.append(delay)
            delay *= 2
        return tuple(result)

    def _delay(self, base: float) -> float:
        if not self.jitter:
            return base
        return max(0.0, base * (1 + self._rng.uniform(-self.jitter, self.jitter)))

    def run(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Call ``func`` until it succeeds, a non-retryable error occurs, or
        ``max_attempts`` calls have been made."""
        if not callable(func):
            raise RetryPolicyError('func must be callable')
        delays = self.delays
        last_error: Optional[BaseException] = None
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except self.retry_on as exc:
                last_error = exc
                if attempt >= len(delays):
                    break
                self._sleep(self._delay(delays[attempt]))
        assert last_error is not None
        raise last_error
