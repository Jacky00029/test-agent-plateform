import unittest

from agent_tools.rate_limiter import RateLimiterError, TokenBucket


class FakeClock:
    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class AcquireTests(unittest.TestCase):
    def test_bucket_allows_burst_up_to_capacity(self):
        bucket = TokenBucket(capacity=3, refill_per_second=1, clock=FakeClock())
        self.assertTrue(bucket.try_acquire())
        self.assertTrue(bucket.try_acquire())
        self.assertTrue(bucket.try_acquire())
        self.assertFalse(bucket.try_acquire())
        self.assertEqual(bucket.tokens, 0)

    def test_failed_acquire_does_not_consume_tokens(self):
        bucket = TokenBucket(capacity=2, refill_per_second=1, clock=FakeClock())
        self.assertTrue(bucket.try_acquire())
        self.assertFalse(bucket.try_acquire(2))
        self.assertEqual(bucket.tokens, 1)
        self.assertFalse(bucket.try_acquire(2))
        self.assertEqual(bucket.tokens, 1)

    def test_successful_acquire_deducts_exact_amount(self):
        bucket = TokenBucket(capacity=5, refill_per_second=1, clock=FakeClock())
        self.assertTrue(bucket.try_acquire(2))
        self.assertEqual(bucket.tokens, 3)
        self.assertTrue(bucket.try_acquire(3))
        self.assertEqual(bucket.tokens, 0)

    def test_refill_never_exceeds_capacity(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=4, refill_per_second=2, clock=clock)
        bucket.try_acquire(4)
        clock.advance(1000)
        self.assertEqual(bucket.tokens, 4)
        self.assertTrue(bucket.try_acquire(4))
        self.assertEqual(bucket.tokens, 0)

    def test_refill_accumulates_by_rate(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=10, refill_per_second=2, clock=clock)
        bucket.try_acquire(10)
        clock.advance(0.5)
        self.assertAlmostEqual(bucket.tokens, 1.0)
        clock.advance(0.25)
        self.assertAlmostEqual(bucket.tokens, 1.5)

    def test_partial_refill_does_not_allow_full_request(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=2, refill_per_second=1, clock=clock)
        bucket.try_acquire(2)
        clock.advance(0.5)
        self.assertFalse(bucket.try_acquire(1))
        self.assertAlmostEqual(bucket.tokens, 0.5)

    def test_clock_advance_allows_new_call(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=1, refill_per_second=1, clock=clock)
        self.assertTrue(bucket.try_acquire())
        self.assertFalse(bucket.try_acquire())
        clock.advance(1)
        self.assertTrue(bucket.try_acquire())

    def test_token_refill_after_failed_acquire(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=2, refill_per_second=1, clock=clock)
        bucket.try_acquire(2)
        self.assertFalse(bucket.try_acquire())
        clock.advance(1)
        self.assertTrue(bucket.try_acquire())


class RetryAfterTests(unittest.TestCase):
    def test_retry_after_is_zero_when_tokens_available(self):
        bucket = TokenBucket(capacity=3, refill_per_second=1, clock=FakeClock())
        self.assertEqual(bucket.retry_after(), 0.0)

    def test_retry_after_uses_refill_rate(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=2, refill_per_second=2, clock=clock)
        bucket.try_acquire(2)
        self.assertEqual(bucket.retry_after(1), 0.5)
        self.assertEqual(bucket.retry_after(2), 1.0)

    def test_retry_after_accounts_for_partial_tokens(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=4, refill_per_second=1, clock=clock)
        bucket.try_acquire(3)
        self.assertAlmostEqual(bucket.retry_after(2), 1.0)
        clock.advance(0.25)
        self.assertAlmostEqual(bucket.retry_after(2), 0.75)

    def test_retry_after_does_not_consume_tokens(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=2, refill_per_second=1, clock=clock)
        bucket.try_acquire(2)
        self.assertEqual(bucket.retry_after(1), 1.0)
        self.assertEqual(bucket.tokens, 0)
        self.assertTrue(bucket.try_acquire() is False)
        clock.advance(1)
        self.assertTrue(bucket.try_acquire())

    def test_retry_after_waits_then_acquire_succeeds(self):
        clock = FakeClock()
        bucket = TokenBucket(capacity=2, refill_per_second=4, clock=clock)
        bucket.try_acquire(2)
        wait = bucket.retry_after(1)
        self.assertAlmostEqual(wait, 0.25)
        clock.advance(wait)
        self.assertTrue(bucket.try_acquire())

    def test_request_above_capacity_is_impossible(self):
        bucket = TokenBucket(capacity=2, refill_per_second=1, clock=FakeClock())
        self.assertEqual(bucket.retry_after(3), float('inf'))
        self.assertFalse(bucket.try_acquire(3))
        self.assertEqual(bucket.tokens, 2)


class ValidationTests(unittest.TestCase):
    def test_invalid_capacity(self):
        for value in (0, -1, '2', None, True, float('nan'), float('inf')):
            with self.assertRaises(RateLimiterError):
                TokenBucket(capacity=value, refill_per_second=1)

    def test_invalid_refill_rate(self):
        for value in (0, -2, '1', False, float('inf')):
            with self.assertRaises(RateLimiterError):
                TokenBucket(capacity=2, refill_per_second=value)

    def test_invalid_clock(self):
        with self.assertRaises(RateLimiterError):
            TokenBucket(capacity=1, refill_per_second=1, clock='now')

    def test_invalid_token_amount(self):
        bucket = TokenBucket(capacity=1, refill_per_second=1, clock=FakeClock())
        for value in (0, -1, '1', True, float('nan')):
            with self.assertRaises(RateLimiterError):
                bucket.try_acquire(value)
            with self.assertRaises(RateLimiterError):
                bucket.retry_after(value)

    def test_exposes_configuration(self):
        bucket = TokenBucket(capacity=2.5, refill_per_second=0.5, clock=FakeClock())
        self.assertEqual(bucket.capacity, 2.5)
        self.assertEqual(bucket.refill_per_second, 0.5)


if __name__ == '__main__':
    unittest.main()
