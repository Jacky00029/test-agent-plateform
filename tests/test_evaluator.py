import unittest

from agent_tools.evaluator import EvaluationError, evaluate


class ExactCheckTests(unittest.TestCase):
    def test_exact_match_passes(self):
        result = evaluate([{'id': 'c1', 'actual': 'hello', 'expected': 'hello', 'check': 'exact'}])
        self.assertEqual(result, {'total': 1, 'passed': 1, 'pass_rate': 1.0, 'failures': []})

    def test_exact_mismatch_reports_reason(self):
        result = evaluate([{'id': 'c1', 'actual': 'hello', 'expected': 'world', 'check': 'exact'}])
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['passed'], 0)
        self.assertEqual(result['pass_rate'], 0.0)
        self.assertEqual(len(result['failures']), 1)
        self.assertEqual(result['failures'][0]['id'], 'c1')
        self.assertEqual(result['failures'][0]['check'], 'exact')
        self.assertIn('world', result['failures'][0]['reason'])
        self.assertIn('hello', result['failures'][0]['reason'])

    def test_exact_is_the_default_check(self):
        result = evaluate([{'id': 'c1', 'actual': 3, 'expected': 3}])
        self.assertEqual(result['passed'], 1)

    def test_exact_keeps_types_distinct(self):
        result = evaluate([{'id': 'c1', 'actual': 1, 'expected': '1', 'check': 'exact'}])
        self.assertEqual(result['passed'], 0)

    def test_none_values(self):
        result = evaluate([{'id': 'c1', 'actual': None, 'expected': None, 'check': 'exact'}])
        self.assertEqual(result['passed'], 1)


class ContainsCheckTests(unittest.TestCase):
    def test_contains_passes_for_substring(self):
        result = evaluate([{'id': 'c1', 'actual': 'agent ready', 'expected': 'ready', 'check': 'contains'}])
        self.assertEqual(result['passed'], 1)

    def test_contains_is_case_sensitive(self):
        result = evaluate([{'id': 'c1', 'actual': 'Agent Ready', 'expected': 'ready', 'check': 'contains'}])
        self.assertEqual(result['passed'], 0)

    def test_contains_works_for_sequences(self):
        result = evaluate([{'id': 'c1', 'actual': ['a', 'b'], 'expected': 'b', 'check': 'contains'}])
        self.assertEqual(result['passed'], 1)

    def test_contains_reports_missing_expected(self):
        result = evaluate([{'id': 'c1', 'actual': 'abc', 'expected': 'z', 'check': 'contains'}])
        self.assertIn('not found', result['failures'][0]['reason'])


class RegexCheckTests(unittest.TestCase):
    def test_regex_searches_actual(self):
        result = evaluate([{'id': 'c1', 'actual': 'order 12345 shipped',
                            'expected': r'\d{5}', 'check': 'regex'}])
        self.assertEqual(result['passed'], 1)

    def test_regex_mismatch_reports_pattern(self):
        result = evaluate([{'id': 'c1', 'actual': 'order pending',
                            'expected': r'\d{5}', 'check': 'regex'}])
        self.assertEqual(result['failures'][0]['id'], 'c1')
        self.assertIn(r'\d{5}', result['failures'][0]['reason'])

    def test_invalid_regex_is_a_configuration_error(self):
        with self.assertRaises(EvaluationError) as caught:
            evaluate([{'id': 'c1', 'actual': 'x', 'expected': '(', 'check': 'regex'}])
        self.assertIn('c1', str(caught.exception))

    def test_regex_expected_must_be_string(self):
        with self.assertRaises(EvaluationError):
            evaluate([{'id': 'c1', 'actual': 'x', 'expected': 1, 'check': 'regex'}])


class JsonEqualsCheckTests(unittest.TestCase):
    def test_json_strings_compare_by_structure(self):
        result = evaluate([{
            'id': 'c1', 'check': 'json_equals',
            'actual': '{"b": 2, "a": [1, {"x": true}]}',
            'expected': '{"a": [1, {"x": true}], "b": 2}',
        }])
        self.assertEqual(result['passed'], 1)

    def test_json_objects_compare_by_structure(self):
        result = evaluate([{
            'id': 'c1', 'check': 'json_equals',
            'actual': {'a': 1, 'b': [2, 3]},
            'expected': {'b': [2, 3], 'a': 1},
        }])
        self.assertEqual(result['passed'], 1)

    def test_json_mismatch_reports_actual_and_expected(self):
        result = evaluate([{
            'id': 'c1', 'check': 'json_equals',
            'actual': '{"status": "fail"}',
            'expected': '{"status": "ok"}',
        }])
        self.assertEqual(result['passed'], 0)
        reason = result['failures'][0]['reason']
        self.assertIn('fail', reason)
        self.assertIn('ok', reason)

    def test_json_array_order_matters(self):
        result = evaluate([{'id': 'c1', 'check': 'json_equals',
                            'actual': [1, 2], 'expected': [2, 1]}])
        self.assertEqual(result['passed'], 0)

    def test_json_object_extra_key_fails(self):
        result = evaluate([{'id': 'c1', 'check': 'json_equals',
                            'actual': {'a': 1, 'b': 2}, 'expected': {'a': 1}}])
        self.assertEqual(result['passed'], 0)

    def test_json_boolean_is_not_a_number(self):
        result = evaluate([{'id': 'c1', 'check': 'json_equals',
                            'actual': True, 'expected': 1}])
        self.assertEqual(result['passed'], 0)

    def test_invalid_json_actual_is_reported(self):
        with self.assertRaises(EvaluationError) as caught:
            evaluate([{'id': 'c1', 'check': 'json_equals',
                       'actual': '{not json', 'expected': '{}'}])
        self.assertIn('c1', str(caught.exception))
        self.assertIn('actual', str(caught.exception))


class MixedCasesTests(unittest.TestCase):
    def test_mixed_cases_only_count_real_passes(self):
        result = evaluate([
            {'id': 'exact-ok', 'actual': 'a', 'expected': 'a', 'check': 'exact'},
            {'id': 'exact-bad', 'actual': 'a', 'expected': 'b', 'check': 'exact'},
            {'id': 'contains-ok', 'actual': 'abc', 'expected': 'b', 'check': 'contains'},
            {'id': 'regex-bad', 'actual': 'abc', 'expected': r'\d', 'check': 'regex'},
            {'id': 'json-ok', 'actual': '{"n": 1}', 'expected': {'n': 1}, 'check': 'json_equals'},
        ])
        self.assertEqual(result['total'], 5)
        self.assertEqual(result['passed'], 3)
        self.assertEqual(result['pass_rate'], 0.6)
        self.assertEqual([row['id'] for row in result['failures']], ['exact-bad', 'regex-bad'])

    def test_failure_entries_have_id_check_and_reason(self):
        result = evaluate([{'id': 'x1', 'actual': 'a', 'expected': 'b', 'check': 'contains'}])
        failure = result['failures'][0]
        self.assertEqual(failure['id'], 'x1')
        self.assertEqual(failure['check'], 'contains')
        self.assertTrue(failure['reason'])

    def test_empty_cases(self):
        self.assertEqual(evaluate([]), {'total': 0, 'passed': 0, 'pass_rate': 0.0, 'failures': []})

    def test_does_not_mutate_cases(self):
        cases = [{'id': 'c1', 'actual': {'a': 1}, 'expected': {'a': 1}, 'check': 'json_equals'}]
        snapshot = [dict(cases[0])]
        evaluate(cases)
        self.assertEqual(cases, snapshot)


class ValidationTests(unittest.TestCase):
    def test_cases_must_be_a_list(self):
        for value in (None, {}, 'cases'):
            with self.assertRaises(EvaluationError):
                evaluate(value)

    def test_case_must_be_object(self):
        with self.assertRaises(EvaluationError):
            evaluate(['not-a-case'])

    def test_case_id_is_required_and_unique(self):
        with self.assertRaises(EvaluationError):
            evaluate([{'actual': 'a', 'expected': 'a'}])
        with self.assertRaises(EvaluationError):
            evaluate([{'id': ' ', 'actual': 'a', 'expected': 'a'}])
        with self.assertRaises(EvaluationError):
            evaluate([{'id': 'c1', 'actual': 'a', 'expected': 'a'},
                      {'id': 'c1', 'actual': 'b', 'expected': 'b'}])

    def test_actual_and_expected_are_required(self):
        with self.assertRaises(EvaluationError):
            evaluate([{'id': 'c1', 'expected': 'a'}])
        with self.assertRaises(EvaluationError):
            evaluate([{'id': 'c1', 'actual': 'a'}])

    def test_unknown_check_is_rejected(self):
        with self.assertRaises(EvaluationError) as caught:
            evaluate([{'id': 'c1', 'actual': 'a', 'expected': 'a', 'check': 'fuzzy'}])
        self.assertIn('c1', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
