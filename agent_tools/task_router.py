"""Explainable keyword routing to agent tools.

Rules are ranked by keyword hit count (descending), then priority
(descending), then registration order. Matching is case-insensitive.
"""
from typing import Any, Dict, Iterable, List, Mapping, Optional


GENERAL = 'general'


class TaskRouterError(ValueError):
    """Raised for invalid routing rules or inputs."""


class TaskRouter:
    """Register named keyword rules and route text to the best match."""

    def __init__(self, rules: Optional[Iterable[Mapping[str, Any]]] = None):
        self._rules: List[Dict[str, Any]] = []
        self._names = set()
        for rule in rules or []:
            if not isinstance(rule, Mapping):
                raise TaskRouterError('rule must be a mapping')
            self.register(rule.get('name'), rule.get('keywords'), rule.get('priority', 0))

    @property
    def rules(self) -> List[Dict[str, Any]]:
        """A defensive copy of the registered rules in registration order."""
        return [
            {'name': rule['name'], 'keywords': list(rule['keywords']),
             'priority': rule['priority']}
            for rule in self._rules
        ]

    def register(self, name: str, keywords: Iterable[str], priority: int = 0) -> 'TaskRouter':
        if not isinstance(name, str) or not name.strip():
            raise TaskRouterError('name must be a non-empty string')
        if name in self._names:
            raise TaskRouterError('duplicate rule name: ' + name)
        if isinstance(keywords, str) or not isinstance(keywords, (list, tuple)):
            raise TaskRouterError('keywords must be a list or tuple of strings')
        normalized = []
        for keyword in keywords:
            if not isinstance(keyword, str) or not keyword.strip():
                raise TaskRouterError('keywords must be non-empty strings')
            lowered = keyword.casefold()
            if lowered in normalized:
                raise TaskRouterError('duplicate keyword: ' + keyword)
            normalized.append(lowered)
        if not normalized:
            raise TaskRouterError('keywords must not be empty')
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise TaskRouterError('priority must be an integer')
        self._rules.append({'name': name, 'keywords': normalized, 'priority': priority})
        self._names.add(name)
        return self

    def route(self, text: str) -> str:
        """Return the best matching rule name, or ``general`` when none match."""
        if not isinstance(text, str):
            raise TypeError('text must be a str')
        lowered = text.casefold()
        best_name = GENERAL
        best_key = None
        for index, rule in enumerate(self._rules):
            hits = sum(1 for keyword in rule['keywords'] if keyword in lowered)
            if hits == 0:
                continue
            key = (hits, rule['priority'], -index)
            if best_key is None or key > best_key:
                best_key = key
                best_name = rule['name']
        return best_name
