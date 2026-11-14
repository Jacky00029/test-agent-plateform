import unittest

from agent_tools.latency_tracker import (
    LatencyTracker,
    LatencyTrackerError,
    nearest_rank,
)


class FakeClock:
    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class SummaryTests(unittest.TestCase):
    def test_summary_contains_all_required_fields(self):
        tracker = LatencyTracker()
        tracker.record('search', 10)
        tracker.record('search', 20)
        summary = tracker.summary('search')
        self.assertEqual(
            set(summary),
            {'tool', 'count', 'error_count', 'error_rate', 'avg_ms',
             'p50_ms', 'p95_ms', 'total_ms'},
        )

    def test_summary_computes_values_for_one_tool(self):
        tracker = LatencyTracker()
        for value in (10, 20, 30, 40):
            tracker.record('search', value)
        summary = tracker.summary('search')
        self.assertEqual(summary['count'], 4)
        self.assertEqual(summary['error_count'], 0)
        self.assertEqual(summary['error_rate'], 0.0)
        self.assertEqual(summary['avg_ms'], 25.0)
        self.assertEqual(summary['p50_ms'], 20.0)
        self.assertEqual(summary['p95_ms'], 40.0)
        self.assertEqual(summary['total_ms'], 100.0)

    def test_error_rate_only_counts_failed_calls(self):
        tracker = LatencyTracker()
        tracker.record('search', 10)
        tracker.record('search', 20, error=True)
        tracker.record('search', 30)
        tracker.record('search', 40, error=True)
        summary = tracker.summary('search')
        self.assertEqual(summary['count'], 4)
        self.assertEqual(summary['error_count'], 2)
        self.assertEqual(summary['error_rate'], 0.5)
        self.assertEqual(summary['total_ms'], 100.0)

    def test_summary_without_tool_aggregates_everything(self):
        tracker = LatencyTracker()
        tracker.record('search', 10)
        tracker.record('fetch', 30, error=True)
        summary = tracker.summary()
        self.assertIsNone(summary['tool'])
        self.assertEqual(summary['count'], 2)
        self.assertEqual(summary['error_count'], 1)
        self.assertEqual(summary['error_rate'], 0.5)
        self.assertEqual(summary['avg_ms'], 20.0)
        self.assertEqual(summary['p50_ms'], 10.0)
        self.assertEqual(summary['p95_ms'], 30.0)
        self.assertEqual(summary['total_ms'], 40.0)

    def test_empty_tool_reports_unknown_statistics(self):
        tracker = LatencyTracker()
        summary = tracker.summary('missing')
        self.assertEqual(summary['count'], 0)
        self.assertEqual(summary['error_count'], 0)
        self.assertEqual(summary['error_rate'], 0.0)
        self.assertEqual(summary['avg_ms'], 'unknown')
        self.assertEqual(summary['p50_ms'], 'unknown')
        self.assertEqual(summary['p95_ms'], 'unknown')
        self.assertEqual(summary['total_ms'], 0.0)

    def test_global_summary_on_empty_tracker_is_unknown(self):
        summary = LatencyTracker().summary()
        self.assertEqual(summary['avg_ms'], 'unknown')
        self.assertEqual(summary['p50_ms'], 'unknown')
        self.assertEqual(summary['p95_ms'], 'unknown')

    def test_single_sample_is_every_percentile(self):
        tracker = LatencyTracker()
        tracker.record('search', 12.5)
        summary = tracker.summary('search')
        self.assertEqual(summary['avg_ms'], 12.5)
        self.assertEqual(summary['p50_ms'], 12.5)
        self.assertEqual(summary['p95_ms'], 12.5)

    def test_reset_clears_one_tool_or_all(self):
        tracker = LatencyTracker()
        tracker.record('search', 10)
        tracker.record('fetch', 20)
        tracker.reset('search')
        self.assertEqual(tracker.summary('search')['count'], 0)
        self.assertEqual(tracker.summary('fetch')['count'], 1)
        tracker.reset()
        self.assertEqual(tracker.summary()['count'], 0)


class NearestRankTests(unittest.TestCase):
    def test_nearest_rank_matches_ceil_rank(self):
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        self.assertEqual(nearest_rank(values, 50), 50)
        self.assertEqual(nearest_rank(values, 95), 100)
        self.assertEqual(nearest_rank(values, 10), 10)
        self.assertEqual(nearest_rank(values, 100), 100)

    def test_nearest_rank_rounds_rank_up(self):
        self.assertEqual(nearest_rank([1, 2, 3], 50), 2)
        self.assertEqual(nearest_rank([1, 2, 3], 95), 3)
        self.assertEqual(nearest_rank([4, 1, 3, 2], 50), 2)
        self.assertEqual(nearest_rank([5, 1, 3], 95), 5)

    def test_nearest_rank_sorts_without_mutating_input(self):
        values = [3, 1, 2]
        self.assertEqual(nearest_rank(values, 50), 2)
        self.assertEqual(values, [3, 1, 2])

    def test_nearest_rank_rejects_bad_input(self):
        with self.assertRaises(LatencyTrackerError):
            nearest_rank([], 50)
        with self.assertRaises(LatencyTrackerError):
            nearest_rank([1], 0)
        with self.assertRaises(LatencyTrackerError):
            nearest_rank([1], 101)
        with self.assertRaises(LatencyTrackerError):
            nearest_rank([1], '50')


class MeasureTests(unittest.TestCase):
    def test_measure_records_successful_duration(self):
        clock = FakeClock()
        tracker = LatencyTracker(clock=clock)

        with tracker.measure('search'):
            clock.advance(0.25)

        summary = tracker.summary('search')
        self.assertEqual(summary['count'], 1)
        self.assertEqual(summary['error_count'], 0)
        self.assertAlmostEqual(summary['avg_ms'], 250.0)

    def test_measure_records_failed_call_and_reraises(self):
        clock = FakeClock()
        tracker = LatencyTracker(clock=clock)

        with self.assertRaises(RuntimeError):
            with tracker.measure('search'):
                clock.advance(0.5)
                raise RuntimeError('boom')

        summary = tracker.summary('search')
        self.assertEqual(summary['count'], 1)
        self.assertEqual(summary['error_count'], 1)
        self.assertEqual(summary['error_rate'], 1.0)
        self.assertAlmostEqual(summary['total_ms'], 500.0)

    def test_measure_records_multiple_calls(self):
        clock = FakeClock()
        tracker = LatencyTracker(clock=clock)
        for seconds in (0.1, 0.2, 0.3):
            with tracker.measure('search'):
                clock.advance(seconds)
        summary = tracker.summary('search')
        self.assertEqual(summary['count'], 3)
        self.assertAlmostEqual(summary['total_ms'], 600.0)
        self.assertAlmostEqual(summary['avg_ms'], 200.0)

    def test_measure_rejects_empty_tool_name(self):
        with self.assertRaises(LatencyTrackerError):
            with LatencyTracker().measure(''):
                pass

    def test_max_samples_keeps_recent_measurements(self):
        tracker = LatencyTracker(max_samples=2)
        for value in (1, 2, 3):
            tracker.record('search', value)
        summary = tracker.summary('search')
        self.assertEqual(summary['count'], 2)
        self.assertEqual(summary['total_ms'], 5.0)


class ValidationTests(unittest.TestCase):
    def test_invalid_tool_name(self):
        tracker = LatencyTracker()
        for value in ('', '   ', None, 1):
            with self.assertRaises(LatencyTrackerError):
                tracker.record(value, 10)

    def test_invalid_duration(self):
        tracker = LatencyTracker()
        for value in (-1, '10', None, True, float('nan'), float('inf')):
            with self.assertRaises(LatencyTrackerError):
                tracker.record('search', value)

    def test_invalid_construction(self):
        with self.assertRaises(LatencyTrackerError):
            LatencyTracker(max_samples=0)
        with self.assertRaises(LatencyTrackerError):
            LatencyTracker(clock='now')

    def test_record_keeps_tool_order(self):
        tracker = LatencyTracker()
        tracker.record('b', 1)
        tracker.record('a', 1)
        self.assertEqual(tracker.tools, ('b', 'a'))


if __name__ == '__main__':
    unittest.main()
