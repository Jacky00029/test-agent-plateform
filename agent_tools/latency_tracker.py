"""Per-tool latency and error statistics for agent tool calls."""
import math
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


Number = (int, float)
UNKNOWN = 'unknown'


class LatencyTrackerError(ValueError):
    """Raised for invalid latency tracker input."""


def _validate_tool(tool: Any) -> str:
    if not isinstance(tool, str) or not tool.strip():
        raise LatencyTrackerError('tool must be a non-empty string')
    return tool


def _validate_duration(duration_ms: Any) -> float:
    if isinstance(duration_ms, bool) or not isinstance(duration_ms, Number):
        raise LatencyTrackerError('duration_ms must be a number')
    if math.isnan(duration_ms) or math.isinf(duration_ms):
        raise LatencyTrackerError('duration_ms must be finite')
    if duration_ms < 0:
        raise LatencyTrackerError('duration_ms must not be negative')
    return float(duration_ms)


def nearest_rank(values: List[float], percentile: float) -> float:
    """Return a percentile using the nearest-rank method.

    ``percentile`` is expressed in percent (e.g. 50 or 95). The rank is
    ``ceil(p / 100 * n)`` and the matching 1-based sample is returned after
    sorting. ``values`` must contain at least one sample.
    """
    if not values:
        raise LatencyTrackerError('percentile requires at least one sample')
    if isinstance(percentile, bool) or not isinstance(percentile, Number):
        raise LatencyTrackerError('percentile must be a number')
    if not 0 < percentile <= 100:
        raise LatencyTrackerError('percentile must be between 0 and 100')
    ordered = sorted(values)
    rank = max(1, min(len(ordered), math.ceil(percentile / 100 * len(ordered))))
    return float(ordered[rank - 1])


class LatencyTracker:
    """Collect durations for named tools and report comparable statistics.

    Successful and failed calls are stored together; failed calls only affect
    ``error_count`` and ``error_rate``. ``summary`` accepts an optional tool
    name and aggregates every tool when it is omitted. Statistics for a tool
    without samples are reported as ``'unknown'``.
    """

    def __init__(self, clock: Optional[Callable[[], float]] = None, max_samples: Optional[int] = None):
        if clock is not None and not callable(clock):
            raise LatencyTrackerError('clock must be callable')
        if max_samples is not None:
            if isinstance(max_samples, bool) or not isinstance(max_samples, int):
                raise LatencyTrackerError('max_samples must be an integer')
            if max_samples < 1:
                raise LatencyTrackerError('max_samples must be at least 1')
        self._clock = clock or time.perf_counter
        self._max_samples = max_samples
        self._samples: Dict[str, List[Tuple[float, bool]]] = {}

    def record(self, tool: str, duration_ms: float, error: bool = False) -> None:
        """Store one measured call duration in milliseconds."""
        tool = _validate_tool(tool)
        duration = _validate_duration(duration_ms)
        samples = self._samples.setdefault(tool, [])
        samples.append((duration, bool(error)))
        if self._max_samples is not None and len(samples) > self._max_samples:
            del samples[0]

    @contextmanager
    def measure(self, tool: str) -> Iterator[None]:
        """Time a block, recording success or failure, and re-raise errors."""
        tool = _validate_tool(tool)
        started = self._clock()
        error = False
        try:
            yield
        except BaseException:
            error = True
            raise
        finally:
            elapsed_ms = (self._clock() - started) * 1000
            self.record(tool, max(0.0, elapsed_ms), error=error)

    @property
    def tools(self) -> Tuple[str, ...]:
        return tuple(self._samples)

    def reset(self, tool: Optional[str] = None) -> None:
        if tool is None:
            self._samples.clear()
            return
        self._samples.pop(_validate_tool(tool), None)

    def summary(self, tool: Optional[str] = None) -> Dict[str, Any]:
        """Return count, error_count, error_rate, avg_ms, p50_ms, p95_ms and
        total_ms for one tool or for the whole tracker."""
        if tool is None:
            durations = [row[0] for samples in self._samples.values() for row in samples]
            errors = sum(1 for samples in self._samples.values() for row in samples if row[1])
        else:
            samples = self._samples.get(_validate_tool(tool), [])
            durations = [row[0] for row in samples]
            errors = sum(1 for row in samples if row[1])
        count = len(durations)
        if count == 0:
            return {'tool': tool, 'count': 0, 'error_count': 0, 'error_rate': 0.0,
                    'avg_ms': UNKNOWN, 'p50_ms': UNKNOWN, 'p95_ms': UNKNOWN, 'total_ms': 0.0}
        total = round(sum(durations), 6)
        return {
            'tool': tool,
            'count': count,
            'error_count': errors,
            'error_rate': round(errors / count, 6),
            'avg_ms': round(total / count, 6),
            'p50_ms': round(nearest_rank(durations, 50), 6),
            'p95_ms': round(nearest_rank(durations, 95), 6),
            'total_ms': total,
        }
