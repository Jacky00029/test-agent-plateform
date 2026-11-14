"""Token-budget aware prompt packing using only the Python standard library.

The estimator intentionally mirrors the common "four characters per token"
approximation. Packing keeps the caller's segment order, never mutates the
input, and never reports more tokens than the supplied budget.
"""
from math import ceil
from typing import Any, Dict, Iterable, List, Mapping, Sequence


class PromptBudgetError(ValueError):
    """Raised when prompt segments or the budget are not usable."""


def estimate_tokens(text: str) -> int:
    """Return 0 for an empty string, otherwise ceil(len(text) / 4)."""
    if not isinstance(text, str):
        raise TypeError('text must be a str')
    if text == '':
        return 0
    return ceil(len(text) / 4)


def _segment_text(segment: Any, index: int) -> str:
    if not isinstance(segment, Mapping):
        raise PromptBudgetError('segment %d must be a mapping' % index)
    if 'text' not in segment:
        raise PromptBudgetError('segment %d is missing text' % index)
    text = segment['text']
    if not isinstance(text, str):
        raise TypeError('segment %d text must be a str' % index)
    return text


def _segment_priority(segment: Mapping[str, Any], index: int) -> int:
    priority = segment.get('priority', 0)
    if isinstance(priority, bool) or not isinstance(priority, int):
        raise PromptBudgetError('segment %d priority must be an integer' % index)
    return priority


def _copy_segment(segment: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(segment)


def pack_prompt(
    segments: Sequence[Mapping[str, Any]],
    budget: int,
) -> Dict[str, Any]:
    """Pack prompt segments into a token budget.

    Each segment is a mapping with a string ``text`` and an optional integer
    ``priority`` (higher values are more important). Segments that fit are kept
    in their original input order. When a segment does not fit, it is skipped
    and later, shorter segments can still use the remaining budget. A segment
    with a higher priority may replace already selected lower-priority
    segments, which are then reported as dropped.

    Returns ``{"segments": [...], "used_tokens": int, "dropped": [...]}``.
    """
    if isinstance(budget, bool) or not isinstance(budget, int):
        raise TypeError('budget must be an integer')
    if budget < 0:
        raise PromptBudgetError('budget must not be negative')
    if not isinstance(segments, (list, tuple)):
        raise TypeError('segments must be a list or tuple')

    texts: List[str] = []
    priorities: List[int] = []
    tokens: List[int] = []
    for index, segment in enumerate(segments):
        text = _segment_text(segment, index)
        texts.append(text)
        priorities.append(_segment_priority(segment, index))
        tokens.append(estimate_tokens(text))

    selected: List[int] = []
    used = 0
    for index, cost in enumerate(tokens):
        if cost <= budget - used:
            selected.append(index)
            used += cost
            continue

        # The segment does not fit. A more important segment may replace
        # lower-priority selections; otherwise it is skipped so later short
        # segments still get a chance.
        removable = [
            chosen for chosen in selected
            if priorities[chosen] < priorities[index]
        ]
        freed = 0
        while cost > budget - (used - freed):
            if not removable:
                break
            victim = min(removable, key=lambda chosen: (priorities[chosen], -chosen))
            removable.remove(victim)
            freed += tokens[victim]
        if cost <= budget - (used - freed):
            removed = {
                chosen for chosen in selected
                if priorities[chosen] < priorities[index]
            }
            # Remove only the minimal victims needed, not every lower-priority
            # segment that happens to be selected.
            needed = used + cost - budget
            victims: List[int] = []
            freed_now = 0
            candidates = sorted(removed, key=lambda chosen: (priorities[chosen], -chosen))
            for candidate in candidates:
                if freed_now >= needed:
                    break
                victims.append(candidate)
                freed_now += tokens[candidate]
            selected = [chosen for chosen in selected if chosen not in victims]
            used -= freed_now
            selected.append(index)
            used += cost

    kept = sorted(selected)
    dropped = [index for index in range(len(segments)) if index not in set(kept)]
    return {
        'segments': [_copy_segment(segments[index]) for index in kept],
        'used_tokens': used,
        'dropped': [_copy_segment(segments[index]) for index in dropped],
    }
