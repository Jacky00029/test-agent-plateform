"""In-memory TTL cache for repeated agent tool results."""
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, Iterator, Optional, Tuple


Number = (int, float)
_UNSET = object()


class TTLCacheError(ValueError):
    """Raised for invalid cache configuration or input."""


def _validate_ttl(value: Any, name: str = 'ttl_seconds') -> float:
    if isinstance(value, bool) or not isinstance(value, Number):
        raise TTLCacheError(name + ' must be a number')
    if value <= 0:
        raise TTLCacheError(name + ' must be greater than 0')
    return float(value)


class TTLCache:
    """Store values with an expiration time and recompute them on demand.

    ``get_or_compute`` reuses a value while it is live and calls the producer
    after it expires. Producer failures never populate the cache. ``len``
    counts only unexpired entries and does not mutate the cache;
    ``purge_expired`` removes expired entries explicitly. When ``maxsize`` is
    set, the least recently used entry is evicted on insert.
    """

    def __init__(self, ttl_seconds: float, clock: Optional[Callable[[], float]] = None,
                 maxsize: Optional[int] = None):
        self._ttl = _validate_ttl(ttl_seconds)
        if clock is not None and not callable(clock):
            raise TTLCacheError('clock must be callable')
        if maxsize is not None:
            if isinstance(maxsize, bool) or not isinstance(maxsize, int):
                raise TTLCacheError('maxsize must be an integer')
            if maxsize < 1:
                raise TTLCacheError('maxsize must be at least 1')
        self._clock = clock or time.monotonic
        self._maxsize = maxsize
        self._entries: 'OrderedDict[Any, Tuple[Any, float]]' = OrderedDict()

    @property
    def ttl_seconds(self) -> float:
        return self._ttl

    def _expired(self, expires_at: float, now: float) -> bool:
        return now >= expires_at

    def get(self, key: Any, default: Any = None) -> Any:
        """Return a live value or ``default``; expired entries are removed."""
        entry = self._entries.get(key)
        if entry is None:
            return default
        value, expires_at = entry
        if self._expired(expires_at, self._clock()):
            del self._entries[key]
            return default
        self._entries.move_to_end(key)
        return value

    def set(self, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        """Store ``value`` for ``ttl`` seconds (defaults to the cache TTL)."""
        duration = self._ttl if ttl is None else _validate_ttl(ttl, 'ttl')
        if self._maxsize is not None:
            self._entries.pop(key, None)
            while len(self._entries) >= self._maxsize:
                self._entries.popitem(last=False)
        self._entries[key] = (value, self._clock() + duration)
        self._entries.move_to_end(key)

    def get_or_compute(self, key: Any, producer: Callable[[], Any],
                       ttl: Optional[float] = None) -> Any:
        """Return a live cached value or compute, store and return a new one.

        ``producer`` must be callable; if it raises, the exception propagates
        and the cache is left untouched.
        """
        value = self.get(key, _UNSET)
        if value is not _UNSET:
            return value
        if not callable(producer):
            raise TTLCacheError('producer must be callable')
        value = producer()
        self.set(key, value, ttl=ttl)
        return value

    def purge_expired(self) -> int:
        """Remove expired entries and return how many were removed."""
        now = self._clock()
        expired = [key for key, (_, expires_at) in self._entries.items()
                   if self._expired(expires_at, now)]
        for key in expired:
            del self._entries[key]
        return len(expired)

    def clear(self) -> None:
        self._entries.clear()

    def items(self) -> Iterator[Tuple[Any, Any]]:
        """Yield live key/value pairs without returning expired entries."""
        now = self._clock()
        for key, (value, expires_at) in list(self._entries.items()):
            if not self._expired(expires_at, now):
                yield key, value

    def __contains__(self, key: Any) -> bool:
        return self.get(key, _UNSET) is not _UNSET

    def __len__(self) -> int:
        now = self._clock()
        return sum(1 for _, expires_at in self._entries.values()
                   if not self._expired(expires_at, now))
