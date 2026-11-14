import unittest

from agent_tools.ttl_cache import TTLCache, TTLCacheError


class FakeClock:
    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeProducer:
    def __init__(self, *values):
        self.values = list(values)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.values:
            value = self.values.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value
        return 'value-%d' % self.calls


class GetOrComputeTests(unittest.TestCase):
    def test_reuses_value_within_ttl(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=10, clock=clock)
        producer = FakeProducer('first')
        self.assertEqual(cache.get_or_compute('k', producer), 'first')
        clock.advance(9.999)
        self.assertEqual(cache.get_or_compute('k', producer), 'first')
        self.assertEqual(producer.calls, 1)

    def test_recomputes_after_ttl_expires(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=10, clock=clock)
        producer = FakeProducer('first', 'second')
        self.assertEqual(cache.get_or_compute('k', producer), 'first')
        clock.advance(10)
        self.assertEqual(cache.get_or_compute('k', producer), 'second')
        self.assertEqual(producer.calls, 2)

    def test_per_call_ttl_overrides_default(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=100, clock=clock)
        producer = FakeProducer('short', 'again')
        cache.get_or_compute('k', producer, ttl=1)
        clock.advance(1)
        self.assertEqual(cache.get_or_compute('k', producer), 'again')

    def test_producer_failure_is_not_cached(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=10, clock=clock)
        producer = FakeProducer(RuntimeError('boom'), 'recovered')
        with self.assertRaises(RuntimeError):
            cache.get_or_compute('k', producer)
        self.assertEqual(len(cache), 0)
        self.assertIsNone(cache.get('k'))
        self.assertEqual(cache.get_or_compute('k', producer), 'recovered')
        self.assertEqual(producer.calls, 2)

    def test_producer_failure_keeps_previous_expired_value_out(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=5, clock=clock)
        producer = FakeProducer('old', ValueError('failed'))
        self.assertEqual(cache.get_or_compute('k', producer), 'old')
        clock.advance(5)
        with self.assertRaises(ValueError):
            cache.get_or_compute('k', producer)
        self.assertIsNone(cache.get('k'))

    def test_missing_producer_must_be_callable(self):
        cache = TTLCache(ttl_seconds=1)
        with self.assertRaises(TTLCacheError):
            cache.get_or_compute('k', 'nope')

    def test_cached_hit_does_not_require_callable(self):
        cache = TTLCache(ttl_seconds=1)
        cache.set('k', 'value')
        self.assertEqual(cache.get_or_compute('k', None), 'value')


class PurgeAndLengthTests(unittest.TestCase):
    def test_purge_expired_removes_only_expired_entries(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=10, clock=clock)
        cache.set('a', 1)
        clock.advance(5)
        cache.set('b', 2)
        clock.advance(5)
        self.assertEqual(cache.purge_expired(), 1)
        self.assertEqual(len(cache), 1)
        self.assertIsNone(cache.get('a'))
        self.assertEqual(cache.get('b'), 2)
        self.assertEqual(cache.purge_expired(), 0)

    def test_len_counts_only_live_entries(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=10, clock=clock)
        cache.set('a', 1)
        cache.set('b', 2)
        self.assertEqual(len(cache), 2)
        clock.advance(10)
        self.assertEqual(len(cache), 0)
        self.assertEqual(cache.purge_expired(), 2)

    def test_len_keeps_expired_entries_until_purged(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=10, clock=clock)
        cache.set('a', 1)
        clock.advance(10)
        self.assertEqual(len(cache), 0)
        clock.now = 0
        self.assertEqual(len(cache), 1)

    def test_items_skips_expired_entries(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=10, clock=clock)
        cache.set('a', 1)
        cache.set('b', 2, ttl=1)
        clock.advance(2)
        self.assertEqual(list(cache.items()), [('a', 1)])

    def test_contains_uses_expiry(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=10, clock=clock)
        cache.set('a', 1)
        self.assertIn('a', cache)
        clock.advance(10)
        self.assertNotIn('a', cache)


class EntryTests(unittest.TestCase):
    def test_get_removes_expired_entry(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=10, clock=clock)
        cache.set('a', 1)
        clock.advance(10)
        self.assertEqual(cache.get('a', 'missing'), 'missing')
        clock.now = 0
        self.assertEqual(len(cache), 0)

    def test_set_replaces_value_and_restarts_ttl(self):
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=10, clock=clock)
        cache.set('a', 1)
        clock.advance(9)
        cache.set('a', 2)
        clock.advance(9)
        self.assertEqual(cache.get('a'), 2)

    def test_clear_removes_everything(self):
        cache = TTLCache(ttl_seconds=10)
        cache.set('a', 1)
        cache.set('b', 2)
        cache.clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(cache.purge_expired(), 0)

    def test_maxsize_evicts_least_recently_used(self):
        cache = TTLCache(ttl_seconds=10, maxsize=2)
        cache.set('a', 1)
        cache.set('b', 2)
        cache.get('a')
        cache.set('c', 3)
        self.assertIsNone(cache.get('b'))
        self.assertEqual(cache.get('a'), 1)
        self.assertEqual(cache.get('c'), 3)
        self.assertEqual(len(cache), 2)


class ValidationTests(unittest.TestCase):
    def test_invalid_default_ttl(self):
        for value in (0, -1, '10', None, True):
            with self.assertRaises(TTLCacheError):
                TTLCache(ttl_seconds=value)

    def test_invalid_per_entry_ttl(self):
        cache = TTLCache(ttl_seconds=10)
        for value in (0, -0.5, '10', False):
            with self.assertRaises(TTLCacheError):
                cache.set('k', 1, ttl=value)

    def test_invalid_clock_and_maxsize(self):
        with self.assertRaises(TTLCacheError):
            TTLCache(ttl_seconds=10, clock='now')
        for value in (0, -1, 2.5, True):
            with self.assertRaises(TTLCacheError):
                TTLCache(ttl_seconds=10, maxsize=value)


if __name__ == '__main__':
    unittest.main()
