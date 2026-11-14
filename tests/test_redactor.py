import unittest

from agent_tools.redactor import (
    REDACTED,
    RedactorError,
    is_sensitive_key,
    redact,
    redact_text,
)


class RedactKeyTests(unittest.TestCase):
    def test_common_sensitive_keys_are_replaced(self):
        payload = {
            'password': 'p@ss',
            'token': 'abc123',
            'api_key': 'key-123',
            'authorization': 'Bearer abc',
            'secret': 's3cr3t',
        }
        self.assertEqual(redact(payload), {key: REDACTED for key in payload})

    def test_key_matching_ignores_case_and_separators(self):
        payload = {
            'PASSWORD': 'a',
            'Api-Key': 'b',
            'X-API-KEY': 'c',
            'client_secret': 'd',
            'accessToken': 'e',
            'Auth': 'f',
        }
        result = redact(payload)
        self.assertTrue(all(value == REDACTED for value in result.values()), result)

    def test_non_sensitive_keys_keep_values(self):
        payload = {'name': 'agent', 'count': 3, 'author': 'alice'}
        self.assertEqual(redact(payload), payload)

    def test_nested_dict_and_list_are_redacted(self):
        payload = {
            'tool': 'search',
            'request': {'headers': {'Authorization': 'Bearer xyz'}, 'password': 'p'},
            'rows': [{'token': 't1'}, {'api_key': 'k1'}, 'plain'],
        }
        result = redact(payload)
        self.assertEqual(result['tool'], 'search')
        self.assertEqual(result['request']['headers']['Authorization'], REDACTED)
        self.assertEqual(result['request']['password'], REDACTED)
        self.assertEqual(result['rows'][0]['token'], REDACTED)
        self.assertEqual(result['rows'][1]['api_key'], REDACTED)
        self.assertEqual(result['rows'][2], 'plain')

    def test_tuples_are_redacted_recursively(self):
        payload = ('ok', {'secret': 'value'}, ('nested', {'token': 't'}))
        result = redact(payload)
        self.assertEqual(result, ('ok', {'secret': REDACTED}, ('nested', {'token': REDACTED})))

    def test_does_not_mutate_input(self):
        payload = {'password': 'p', 'nested': {'token': 't'}, 'rows': [{'secret': 's'}]}
        original = {'password': 'p', 'nested': {'token': 't'}, 'rows': [{'secret': 's'}]}
        result = redact(payload)
        self.assertEqual(payload, original)
        self.assertIsNot(result, payload)
        self.assertIsNot(result['nested'], payload['nested'])

    def test_non_string_keys_are_preserved(self):
        payload = {1: 'one', None: 'none', ('token',): 't'}
        self.assertEqual(redact(payload), payload)

    def test_scalar_values_are_returned_unchanged(self):
        for value in (None, True, 0, 3.5):
            self.assertEqual(redact(value), value)

    def test_circular_reference_is_cut_off(self):
        payload = {'token': 't'}
        payload['self'] = payload
        result = redact(payload)
        self.assertEqual(result['token'], REDACTED)
        self.assertEqual(result['self'], '[Circular]')


class RedactTextTests(unittest.TestCase):
    def test_bearer_credential_is_replaced(self):
        self.assertEqual(redact_text('Authorization: Bearer abc.def-123'),
                         'Authorization: Bearer [REDACTED]')

    def test_bearer_match_is_case_insensitive(self):
        self.assertEqual(redact_text('bearer TOKEN'), 'Bearer [REDACTED]')
        self.assertEqual(redact_text('BEARER abc'), 'Bearer [REDACTED]')

    def test_multiple_bearer_values_are_replaced(self):
        text = 'a=Bearer one; b=Bearer two=='
        self.assertEqual(redact_text(text), 'a=Bearer [REDACTED]; b=Bearer [REDACTED]')

    def test_text_without_bearer_is_unchanged(self):
        for text in ('plain text', 'token=abc', 'Bearer'):
            self.assertEqual(redact_text(text), text)

    def test_text_is_idempotent(self):
        once = redact_text('Authorization: Bearer abc123')
        self.assertEqual(redact_text(once), once)
        self.assertEqual(redact_text(redact_text(once)), once)

    def test_embedded_bearer_is_redacted_in_structures(self):
        payload = {'message': 'call failed with Bearer abc123'}
        self.assertEqual(redact(payload)['message'], 'call failed with Bearer [REDACTED]')

    def test_redact_is_idempotent_for_structures(self):
        payload = {'token': 'abc', 'headers': {'authorization': 'Bearer x'},
                   'rows': [{'api_key': 'k'}], 'note': 'Bearer y'}
        once = redact(payload)
        self.assertEqual(redact(once), once)

    def test_redact_text_requires_string(self):
        for value in (None, 1, b'bytes', ['x']):
            with self.assertRaises(RedactorError):
                redact_text(value)


class SensitiveKeyTests(unittest.TestCase):
    def test_sensitive_key_detection(self):
        for key in ('password', 'PASSWORD', 'api-key', 'x-api-key', 'access_token',
                    'clientSecret', 'authorization', 'secret', 'credentials'):
            self.assertTrue(is_sensitive_key(key), key)

    def test_normal_keys_are_not_sensitive(self):
        for key in ('author', 'count', 'tool', 'consumer', 'name', ''):
            self.assertFalse(is_sensitive_key(key), key)

    def test_non_string_key_is_not_sensitive(self):
        self.assertFalse(is_sensitive_key(1))
        self.assertFalse(is_sensitive_key(None))


if __name__ == '__main__':
    unittest.main()
