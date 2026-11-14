"""Recursively redact credentials from agent tool results."""
import re
from typing import Any, Dict, Set


REDACTED = '[REDACTED]'
CIRCULAR = '[Circular]'

SENSITIVE_KEYS = frozenset({
    'auth', 'authentication', 'authorization', 'password', 'passwd', 'pwd',
    'token', 'secret', 'apikey', 'credential', 'credentials', 'cookie',
})
SENSITIVE_MARKERS = ('password', 'passwd', 'token', 'apikey', 'authorization',
                     'secret', 'credential', 'sessionid')

_BEARER = re.compile(r'(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*')


class RedactorError(TypeError):
    """Raised when a value cannot be redacted."""


def _normalize_key(key: str) -> str:
    return re.sub(r'[^a-z0-9]', '', key.lower())


def is_sensitive_key(key: Any) -> bool:
    """Return True for key names that carry credentials.

    Matching ignores case and the separators ``_``, ``-``, ``.`` and spaces,
    so ``api_key``, ``apiKey`` and ``X-API-KEY`` all match.
    """
    if not isinstance(key, str):
        return False
    normalized = _normalize_key(key)
    return normalized in SENSITIVE_KEYS or any(marker in normalized for marker in SENSITIVE_MARKERS)


def redact_text(text: str) -> str:
    """Replace the credential after ``Bearer`` with ``[REDACTED]``."""
    if not isinstance(text, str):
        raise RedactorError('redact_text requires a string')
    return _BEARER.sub('Bearer ' + REDACTED, text)


def _redact(value: Any, seen: Set[int]) -> Any:
    if isinstance(value, dict):
        if id(value) in seen:
            return CIRCULAR
        seen.add(id(value))
        try:
            return {key: (REDACTED if is_sensitive_key(key) else _redact(item, seen))
                    for key, item in value.items()}
        finally:
            seen.discard(id(value))
    if isinstance(value, list):
        if id(value) in seen:
            return CIRCULAR
        seen.add(id(value))
        try:
            return [_redact(item, seen) for item in value]
        finally:
            seen.discard(id(value))
    if isinstance(value, tuple):
        if id(value) in seen:
            return CIRCULAR
        seen.add(id(value))
        try:
            return tuple(_redact(item, seen) for item in value)
        finally:
            seen.discard(id(value))
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact(value: Any) -> Any:
    """Return a redacted copy without mutating ``value``.

    Sensitive dictionary keys are replaced by ``[REDACTED]`` at any nesting
    depth; lists and tuples are traversed recursively and plain strings are
    passed through ``redact_text`` so inline Bearer credentials are removed.
    """
    return _redact(value, set())
