import random
import unittest

from agent_tools.retry_policy import RetryPolicy, RetryPolicyError


class DelayTests(unittest.TestCase):
    def test_delays_grow_exponentially(self):
        policy = RetryPolicy(max_attempts=5, base_delay=0.5, max_delay=10)
        self.assertEqual(policy.delays, (0.5, 1.0, 2.0, 4.0))

    def test_delays_are_capped_by_max_delay(self):
        policy = RetryPolicy(max_attempts=5, base_delay=1, max_delay=2)
        self.assertEqual(policy.delays, (1.0, 2.0, 2.0, 2.0))

    def test_single_attempt_has_no_delay(self):
        policy = RetryPolicy(max_attempts=1)
        self.assertEqual(policy.delays, ())
        calls = []
        policy.run(lambda: calls.append(1) or 'done')
        self.assertEqual(calls, [1])

    def test_zero_base_delay_stays_zero(self):
        policy = RetryPolicy(max_attempts=3, base_delay=0, max_delay=1)
        self.assertEqual(policy.delays, (0.0, 0.0))

    def test_max_attempts_controls_total_calls(self):
        sleeps = []
        policy = RetryPolicy(max_attempts=3, base_delay=0.1, sleep=sleeps.append)
        calls = []

        def always_fails():
            calls.append(1)
            raise RuntimeError('attempt %d' % len(calls))

        with self.assertRaises(RuntimeError):
            policy.run(always_fails)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [0.1, 0.2])


class RunTests(unittest.TestCase):
    def test_success_returns_immediately_without_sleeping(self):
        sleeps = []
        policy = RetryPolicy(max_attempts=3, sleep=sleeps.append)
        self.assertEqual(policy.run(lambda a, b=0: a + b, 2, b=3), 5)
        self.assertEqual(sleeps, [])

    def test_retries_specified_exception_then_succeeds(self):
        sleeps = []
        policy = RetryPolicy(max_attempts=3, base_delay=0.25, sleep=sleeps.append)
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError('transient')
            return 'ok'

        self.assertEqual(policy.run(flaky), 'ok')
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [0.25, 0.5])

    def test_keeps_and_raises_last_exception(self):
        policy = RetryPolicy(max_attempts=3, base_delay=0, sleep=lambda _: None)
        errors = [ValueError('first'), ValueError('second'), ValueError('third')]
        calls = []

        def always_fails():
            error = errors[len(calls)]
            calls.append(1)
            raise error

        with self.assertRaises(ValueError) as caught:
            policy.run(always_fails)
        self.assertIs(caught.exception, errors[-1])
        self.assertEqual(str(caught.exception), 'third')

    def test_non_retryable_exception_is_not_retried(self):
        sleeps = []
        policy = RetryPolicy(max_attempts=5, retry_on=(RuntimeError,), sleep=sleeps.append)
        calls = []

        def fails():
            calls.append(1)
            raise KeyError('not transient')

        with self.assertRaises(KeyError):
            policy.run(fails)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sleeps, [])

    def test_single_exception_type_is_supported(self):
        policy = RetryPolicy(max_attempts=2, base_delay=0, retry_on=RuntimeError,
                             sleep=lambda _: None)
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError('once')
            return 'ok'

        self.assertEqual(policy.run(flaky), 'ok')
        self.assertEqual(len(calls), 2)

    def test_jitter_stays_within_configured_ratio(self):
        sleeps = []
        policy = RetryPolicy(max_attempts=2, base_delay=1, max_delay=1, jitter=0.5,
                             sleep=sleeps.append, rng=random.Random(7))
        with self.assertRaises(RuntimeError):
            policy.run(lambda: (_ for _ in ()).throw(RuntimeError('x')))
        self.assertEqual(len(sleeps), 1)
        self.assertGreaterEqual(sleeps[0], 0.5)
        self.assertLessEqual(sleeps[0], 1.5)

    def test_run_requires_callable(self):
        with self.assertRaises(RetryPolicyError):
            RetryPolicy().run('not-callable')


class ConfigurationTests(unittest.TestCase):
    def test_invalid_max_attempts(self):
        for value in (0, -1, True, 2.5, '3'):
            with self.assertRaises(RetryPolicyError):
                RetryPolicy(max_attempts=value)

    def test_invalid_delays_and_jitter(self):
        with self.assertRaises(RetryPolicyError):
            RetryPolicy(base_delay=-0.1)
        with self.assertRaises(RetryPolicyError):
            RetryPolicy(max_delay=-1)
        with self.assertRaises(RetryPolicyError):
            RetryPolicy(jitter=-0.1)
        with self.assertRaises(RetryPolicyError):
            RetryPolicy(jitter=1.1)

    def test_invalid_retry_on(self):
        for value in ('RuntimeError', (), (RuntimeError, 'x'), (object,)):
            with self.assertRaises(RetryPolicyError):
                RetryPolicy(retry_on=value)


if __name__ == '__main__':
    unittest.main()
