"""Fit conversation messages into a token budget.

Leading system messages are always retained. The remaining budget is filled
from the newest message backwards, keeping a contiguous recent suffix. The
input list and its message dictionaries are never mutated.
"""
import copy
from math import ceil
from typing import Any, Dict, List, Mapping, Sequence


class ConversationWindowError(ValueError):
    """Raised when messages or the token budget are not usable."""


def estimate_tokens(text: str) -> int:
    """Estimate tokens as ceil(len(text) / 4), with the empty string at zero."""
    if not isinstance(text, str):
        raise TypeError('text must be a str')
    if text == '':
        return 0
    return ceil(len(text) / 4)


def _message(entry: Any, index: int) -> Mapping[str, Any]:
    if not isinstance(entry, Mapping):
        raise ConversationWindowError('message %d must be a mapping' % index)
    if 'content' not in entry:
        raise ConversationWindowError('message %d is missing content' % index)
    if not isinstance(entry['content'], str):
        raise TypeError('message %d content must be a str' % index)
    role = entry.get('role')
    if role is not None and not isinstance(role, str):
        raise ConversationWindowError('message %d role must be a str' % index)
    return entry


def _copy(entry: Mapping[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(dict(entry))


def fit_messages(
    messages: Sequence[Mapping[str, Any]],
    budget: int,
) -> Dict[str, Any]:
    """Return ``{"window": [...], "dropped": int, "used_tokens": int}``.

    All leading messages whose role is ``system`` are kept first, even if they
    alone exceed ``budget`` (system instructions take precedence). Remaining
    messages are considered newest-first; the first message that does not fit
    stops the window so the retained conversation stays contiguous.
    """
    if isinstance(budget, bool) or not isinstance(budget, int):
        raise TypeError('budget must be an integer')
    if budget < 0:
        raise ConversationWindowError('budget must not be negative')
    if not isinstance(messages, (list, tuple)):
        raise TypeError('messages must be a list or tuple')

    checked = [_message(entry, index) for index, entry in enumerate(messages)]
    costs = [estimate_tokens(entry['content']) for entry in checked]

    system_count = 0
    while system_count < len(checked) and checked[system_count].get('role') == 'system':
        system_count += 1

    used = sum(costs[:system_count])
    selected: List[int] = list(range(system_count))
    remaining = budget - used
    for index in range(len(checked) - 1, system_count - 1, -1):
        cost = costs[index]
        if cost > max(remaining, 0):
            break
        selected.append(index)
        remaining -= cost

    ordered = selected[:system_count] + sorted(selected[system_count:])
    window = [_copy(checked[index]) for index in ordered]
    return {
        'window': window,
        'dropped': len(checked) - len(window),
        'used_tokens': used + sum(costs[index] for index in ordered[system_count:]),
    }
