"""Validate agent tool arguments against a small JSON Schema subset.

Supported types are string, integer, number, boolean, array and object.
Validation returns a deep copy of the caller's arguments and never mutates
either the arguments or the schema.
"""
import copy
from typing import Any, Dict, Mapping


class ToolCallError(ValueError):
    """A tool argument error tied to a concrete field path."""

    def __init__(self, field: str, message: str):
        self.field = field or ''
        self.message = message
        text = (self.field + ': ' + message) if self.field else message
        super().__init__(text)


_SUPPORTED_TYPES = ('string', 'integer', 'number', 'boolean', 'array', 'object')


def _join(prefix: str, field: str) -> str:
    return field if not prefix else prefix + '.' + field


def _schema_type(schema: Mapping[str, Any], path: str) -> str:
    value = schema.get('type')
    if not isinstance(value, str):
        raise ToolCallError(path, 'schema type must be a string')
    if value not in _SUPPORTED_TYPES:
        raise ToolCallError(path, 'unsupported type: ' + value)
    return value


def _check_type(value: Any, expected: str, path: str) -> None:
    if expected == 'string':
        valid = isinstance(value, str)
    elif expected == 'integer':
        valid = isinstance(value, int) and not isinstance(value, bool)
    elif expected == 'number':
        valid = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected == 'boolean':
        valid = isinstance(value, bool)
    elif expected == 'array':
        valid = isinstance(value, list)
    else:
        valid = isinstance(value, dict)
    if not valid:
        raise ToolCallError(path, 'expected ' + expected + ', got ' + type(value).__name__)


def _validate(schema: Mapping[str, Any], value: Any, path: str) -> Any:
    if not isinstance(schema, Mapping):
        raise ToolCallError(path, 'schema must be an object')
    expected = _schema_type(schema, path)
    _check_type(value, expected, path)

    if expected == 'array':
        items = schema.get('items')
        if items is None:
            return copy.deepcopy(value)
        if not isinstance(items, Mapping):
            raise ToolCallError(path, 'schema items must be an object')
        return [_validate(items, item, path + '[' + str(index) + ']')
                for index, item in enumerate(value)]

    if expected == 'object':
        properties = schema.get('properties', {})
        if not isinstance(properties, Mapping):
            raise ToolCallError(path, 'schema properties must be an object')
        required = schema.get('required', [])
        if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
            raise ToolCallError(path, 'schema required must be an array of strings')
        additional = schema.get('additionalProperties', False)
        if additional not in (True, False):
            raise ToolCallError(path, 'additionalProperties must be a boolean')

        result: Dict[str, Any] = {}
        for name in required:
            if name not in value:
                raise ToolCallError(_join(path, name), 'missing required field')
        for name, item in value.items():
            child_path = _join(path, name)
            if name in properties:
                result[name] = _validate(properties[name], item, child_path)
            elif additional:
                result[name] = copy.deepcopy(item)
            else:
                raise ToolCallError(child_path, 'unexpected field')
        return result

    return copy.deepcopy(value)


def validate_call(schema: Mapping[str, Any], arguments: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate ``arguments`` and return an independent copy.

    Raises :class:`ToolCallError` with ``field`` set to the offending field
    path for missing required fields, type mismatches and undeclared fields.
    """
    if not isinstance(schema, Mapping):
        raise ToolCallError('', 'schema must be an object')
    if not isinstance(arguments, Mapping):
        raise ToolCallError('', 'arguments must be an object')
    expected = _schema_type(schema, '')
    if expected != 'object':
        raise ToolCallError('', 'tool arguments schema must be an object')
    return _validate(schema, arguments, '')
