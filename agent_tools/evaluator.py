"""Composable rule evaluation for agent output."""
import json
import re
from typing import Any, Dict, List, Tuple


CHECKS = ('exact', 'contains', 'regex', 'json_equals')
_MAX_REASON = 200


class EvaluationError(ValueError):
    """Raised when evaluation cases are malformed."""


def _preview(value: Any) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            text = repr(value)
    return text if len(text) <= _MAX_REASON else text[:_MAX_REASON] + '...'


def _json_value(value: Any, field: str) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError as exc:
            raise EvaluationError('%s is not valid JSON: %s' % (field, exc))
    return value


def _json_equal(left: Any, right: Any) -> bool:
    """Compare JSON structures without conflating booleans and numbers."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(_json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _json_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, (dict, list)) or isinstance(right, (dict, list)):
        return False
    return left == right


def _check(case: Dict[str, Any]) -> Tuple[bool, str]:
    check = case.get('check', 'exact')
    if check not in CHECKS:
        raise EvaluationError('unknown check: %r' % (check,))
    actual = case['actual']
    expected = case['expected']
    if check == 'exact':
        if actual == expected:
            return True, ''
        return False, 'exact mismatch: expected %s, got %s' % (_preview(expected), _preview(actual))
    if check == 'contains':
        try:
            found = expected in actual
        except TypeError:
            return False, 'contains requires a string or sequence actual and expected'
        if found:
            return True, ''
        return False, "contains mismatch: %s not found in %s" % (_preview(expected), _preview(actual))
    if check == 'regex':
        if not isinstance(expected, str):
            raise EvaluationError('regex expected must be a pattern string')
        try:
            matched = re.search(expected, actual if isinstance(actual, str) else str(actual))
        except re.error as exc:
            raise EvaluationError('invalid regex pattern: %s' % exc)
        if matched:
            return True, ''
        return False, 'regex mismatch: pattern %s did not match %s' % (
            _preview(expected), _preview(actual))
    actual_json = _json_value(actual, 'actual')
    expected_json = _json_value(expected, 'expected')
    if _json_equal(actual_json, expected_json):
        return True, ''
    return False, 'json_equals mismatch: expected %s, got %s' % (
        _preview(expected_json), _preview(actual_json))


def evaluate(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate cases and return total, passed, pass_rate and failures.

    Each case requires a unique ``id``, an ``actual`` value and an
    ``expected`` value. ``check`` selects ``exact`` (default), ``contains``,
    ``regex`` (``expected`` is a pattern searched in ``actual``) or
    ``json_equals`` (strings are parsed as JSON and compared structurally).
    Failures include the case id and the observed reason.
    """
    if not isinstance(cases, (list, tuple)):
        raise EvaluationError('cases must be a list')
    total = len(cases)
    passed = 0
    failures = []
    seen = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise EvaluationError('case at index %d must be an object' % index)
        case_id = case.get('id')
        if not isinstance(case_id, str) or not case_id.strip():
            raise EvaluationError('case at index %d needs a non-empty string id' % index)
        if case_id in seen:
            raise EvaluationError('duplicate case id: ' + case_id)
        seen.add(case_id)
        if 'actual' not in case:
            raise EvaluationError('case %s is missing actual' % case_id)
        if 'expected' not in case:
            raise EvaluationError('case %s is missing expected' % case_id)
        try:
            matched, reason = _check(case)
        except EvaluationError as exc:
            raise EvaluationError('case %s: %s' % (case_id, exc))
        if matched:
            passed += 1
        else:
            failures.append({'id': case_id, 'check': case.get('check', 'exact'), 'reason': reason})
    return {
        'total': total,
        'passed': passed,
        'pass_rate': round(passed / total, 6) if total else 0.0,
        'failures': failures,
    }
