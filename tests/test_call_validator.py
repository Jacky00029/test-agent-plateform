import copy
import unittest

from agent_tools.call_validator import ToolCallError, validate_call


class RequiredFieldTests(unittest.TestCase):
    def test_missing_required_field_reports_field_name(self):
        schema = {
            'type': 'object',
            'properties': {'name': {'type': 'string'}},
            'required': ['name'],
        }
        with self.assertRaises(ToolCallError) as caught:
            validate_call(schema, {})
        self.assertEqual(caught.exception.field, 'name')
        self.assertIn('name', str(caught.exception))

    def test_nested_missing_required_field_uses_dotted_path(self):
        schema = {
            'type': 'object',
            'properties': {
                'user': {
                    'type': 'object',
                    'properties': {'name': {'type': 'string'}},
                    'required': ['name'],
                }
            },
            'required': ['user'],
        }
        with self.assertRaises(ToolCallError) as caught:
            validate_call(schema, {'user': {}})
        self.assertEqual(caught.exception.field, 'user.name')


class TypeErrorTests(unittest.TestCase):
    def test_type_mismatch_reports_field_name(self):
        schema = {
            'type': 'object',
            'properties': {'count': {'type': 'integer'}},
            'required': ['count'],
        }
        with self.assertRaises(ToolCallError) as caught:
            validate_call(schema, {'count': 'many'})
        self.assertEqual(caught.exception.field, 'count')
        self.assertIn('integer', str(caught.exception))

    def test_array_item_type_error_uses_indexed_path(self):
        schema = {
            'type': 'object',
            'properties': {'tags': {'type': 'array', 'items': {'type': 'string'}}},
        }
        with self.assertRaises(ToolCallError) as caught:
            validate_call(schema, {'tags': ['ok', 2]})
        self.assertEqual(caught.exception.field, 'tags[1]')

    def test_integer_rejects_bool_and_float(self):
        schema = {'type': 'object', 'properties': {'value': {'type': 'integer'}}}
        for bad in (True, 1.5):
            with self.assertRaises(ToolCallError):
                validate_call(schema, {'value': bad})

    def test_number_accepts_int_and_float_but_rejects_bool(self):
        schema = {'type': 'object', 'properties': {'value': {'type': 'number'}}}
        self.assertEqual(validate_call(schema, {'value': 2}), {'value': 2})
        self.assertEqual(validate_call(schema, {'value': 2.5}), {'value': 2.5})
        with self.assertRaises(ToolCallError):
            validate_call(schema, {'value': False})

    def test_boolean_accepts_only_bool(self):
        schema = {'type': 'object', 'properties': {'value': {'type': 'boolean'}}}
        self.assertEqual(validate_call(schema, {'value': True}), {'value': True})
        for bad in (0, 1, 'true'):
            with self.assertRaises(ToolCallError):
                validate_call(schema, {'value': bad})


class UndeclaredFieldTests(unittest.TestCase):
    def test_undeclared_field_reports_field_name(self):
        schema = {'type': 'object', 'properties': {'name': {'type': 'string'}}}
        with self.assertRaises(ToolCallError) as caught:
            validate_call(schema, {'name': 'ok', 'extra': 1})
        self.assertEqual(caught.exception.field, 'extra')
        self.assertIn('unexpected', str(caught.exception))

    def test_nested_undeclared_field(self):
        schema = {
            'type': 'object',
            'properties': {'user': {'type': 'object', 'properties': {}}},
        }
        with self.assertRaises(ToolCallError) as caught:
            validate_call(schema, {'user': {'role': 'admin'}})
        self.assertEqual(caught.exception.field, 'user.role')

    def test_additional_properties_true_keeps_extra_fields(self):
        schema = {
            'type': 'object',
            'properties': {'name': {'type': 'string'}},
            'additionalProperties': True,
        }
        result = validate_call(schema, {'name': 'ok', 'extra': {'nested': [1]}})
        self.assertEqual(result, {'name': 'ok', 'extra': {'nested': [1]}})


class SupportedTypeTests(unittest.TestCase):
    def test_all_supported_types_validate(self):
        schema = {
            'type': 'object',
            'properties': {
                'text': {'type': 'string'},
                'count': {'type': 'integer'},
                'ratio': {'type': 'number'},
                'enabled': {'type': 'boolean'},
                'items': {'type': 'array', 'items': {'type': 'integer'}},
                'meta': {
                    'type': 'object',
                    'properties': {'name': {'type': 'string'}},
                    'required': ['name'],
                },
            },
            'required': ['text', 'count', 'ratio', 'enabled', 'items', 'meta'],
        }
        arguments = {
            'text': 'hello',
            'count': 3,
            'ratio': 0.5,
            'enabled': False,
            'items': [1, 2],
            'meta': {'name': 'n'},
        }
        result = validate_call(schema, arguments)
        self.assertEqual(result, arguments)
        self.assertIsNot(result, arguments)
        self.assertIsNot(result['items'], arguments['items'])
        self.assertIsNot(result['meta'], arguments['meta'])

    def test_array_without_items_accepts_any_values(self):
        schema = {'type': 'object', 'properties': {'items': {'type': 'array'}}}
        self.assertEqual(validate_call(schema, {'items': [1, 'x', {'a': 2}]}),
                         {'items': [1, 'x', {'a': 2}]})

    def test_empty_object_schema_accepts_empty_arguments(self):
        self.assertEqual(validate_call({'type': 'object'}, {}), {})

    def test_arguments_are_not_mutated(self):
        schema = {
            'type': 'object',
            'properties': {
                'nested': {'type': 'object', 'properties': {'values': {'type': 'array'}}},
            },
            'additionalProperties': True,
        }
        arguments = {'nested': {'values': [1, 2]}, 'extra': {'k': 'v'}}
        before = copy.deepcopy(arguments)
        result = validate_call(schema, arguments)
        self.assertEqual(arguments, before)
        result['nested']['values'].append(3)
        result['extra']['k'] = 'changed'
        self.assertEqual(arguments, before)

    def test_schema_is_not_mutated(self):
        schema = {
            'type': 'object',
            'properties': {'items': {'type': 'array', 'items': {'type': 'integer'}}},
            'required': ['items'],
        }
        before = copy.deepcopy(schema)
        validate_call(schema, {'items': [1]})
        self.assertEqual(schema, before)


class InvalidCallTests(unittest.TestCase):
    def test_arguments_must_be_object(self):
        with self.assertRaises(ToolCallError) as caught:
            validate_call({'type': 'object'}, ['not', 'an', 'object'])
        self.assertEqual(caught.exception.field, '')

    def test_root_schema_must_be_object_type(self):
        with self.assertRaises(ToolCallError):
            validate_call({'type': 'string'}, {})
        with self.assertRaises(ToolCallError):
            validate_call({}, {})

    def test_unsupported_schema_type(self):
        with self.assertRaises(ToolCallError) as caught:
            validate_call({'type': 'object', 'properties': {'v': {'type': 'date'}}},
                          {'v': '2026-01-01'})
        self.assertEqual(caught.exception.field, 'v')
        self.assertIn('unsupported', str(caught.exception))

    def test_invalid_schema_shapes(self):
        with self.assertRaises(ToolCallError):
            validate_call('not-a-schema', {})
        with self.assertRaises(ToolCallError):
            validate_call({'type': 'object', 'properties': []}, {})
        with self.assertRaises(ToolCallError):
            validate_call({'type': 'object', 'required': 'name'}, {})
        with self.assertRaises(ToolCallError):
            validate_call({'type': 'object', 'additionalProperties': 'yes'}, {})
        with self.assertRaises(ToolCallError):
            validate_call({'type': 'object', 'properties': {'v': {'type': 'array', 'items': []}}},
                          {'v': []})

    def test_error_is_value_error(self):
        with self.assertRaises(ValueError):
            validate_call({'type': 'object', 'required': ['x']}, {})


if __name__ == '__main__':
    unittest.main()
