import copy
import unittest

from agent_tools.conversation_window import (
    ConversationWindowError,
    estimate_tokens,
    fit_messages,
)


class EstimateTokensTests(unittest.TestCase):
    def test_empty_and_non_empty(self):
        self.assertEqual(estimate_tokens(''), 0)
        self.assertEqual(estimate_tokens('abcd'), 1)
        self.assertEqual(estimate_tokens('abcde'), 2)

    def test_non_string_is_rejected(self):
        with self.assertRaises(TypeError):
            estimate_tokens(None)


class FitMessagesTests(unittest.TestCase):
    def test_system_is_kept_and_recent_messages_fill_the_budget(self):
        messages = [
            {'role': 'system', 'content': 'sys!'},
            {'role': 'user', 'content': 'aaaa'},
            {'role': 'assistant', 'content': 'bbbbbbbb'},
            {'role': 'user', 'content': 'cccc'},
        ]
        result = fit_messages(messages, 4)
        self.assertEqual([row['content'] for row in result['window']],
                         ['sys!', 'bbbbbbbb', 'cccc'])
        self.assertEqual([row['role'] for row in result['window']],
                         ['system', 'assistant', 'user'])
        self.assertEqual(result['dropped'], 1)
        self.assertEqual(result['used_tokens'], 4)

    def test_system_is_kept_even_when_it_exceeds_budget(self):
        messages = [
            {'role': 'system', 'content': 's' * 12},
            {'role': 'user', 'content': 'uuuu'},
        ]
        result = fit_messages(messages, 2)
        self.assertEqual([row['content'] for row in result['window']], ['s' * 12])
        self.assertEqual(result['dropped'], 1)
        self.assertEqual(result['used_tokens'], 3)

    def test_multiple_leading_system_messages_are_all_kept(self):
        messages = [
            {'role': 'system', 'content': 'aaaa'},
            {'role': 'system', 'content': 'bbbb'},
            {'role': 'user', 'content': 'cccc'},
        ]
        result = fit_messages(messages, 2)
        self.assertEqual([row['content'] for row in result['window']], ['aaaa', 'bbbb'])
        self.assertEqual(result['dropped'], 1)

    def test_system_after_the_leading_run_is_optional(self):
        messages = [
            {'role': 'user', 'content': 'aaaa'},
            {'role': 'system', 'content': 'bbbb'},
        ]
        result = fit_messages(messages, 1)
        self.assertEqual([row['content'] for row in result['window']], ['bbbb'])
        self.assertEqual(result['dropped'], 1)

    def test_newest_message_that_does_not_fit_stops_the_window(self):
        messages = [
            {'role': 'system', 'content': 'sys!'},
            {'role': 'user', 'content': 'old!'},
            {'role': 'assistant', 'content': 'x' * 12},
        ]
        result = fit_messages(messages, 2)
        self.assertEqual([row['content'] for row in result['window']], ['sys!'])
        self.assertEqual(result['dropped'], 2)
        self.assertEqual(result['used_tokens'], 1)

    def test_empty_messages(self):
        self.assertEqual(fit_messages([], 10),
                         {'window': [], 'dropped': 0, 'used_tokens': 0})

    def test_zero_budget_drops_optional_messages(self):
        messages = [
            {'role': 'user', 'content': 'aaaa'},
            {'role': 'assistant', 'content': 'bbbb'},
        ]
        result = fit_messages(messages, 0)
        self.assertEqual(result['window'], [])
        self.assertEqual(result['dropped'], 2)
        self.assertEqual(result['used_tokens'], 0)

    def test_input_is_not_mutated_and_window_is_copied(self):
        messages = [
            {'role': 'system', 'content': 'sys!', 'meta': {'k': 'v'}},
            {'role': 'user', 'content': 'aaaa', 'meta': {'k': 'v'}},
        ]
        before = copy.deepcopy(messages)
        result = fit_messages(messages, 10)
        self.assertEqual(messages, before)
        self.assertIsNot(result['window'][0], messages[0])
        result['window'][0]['meta']['k'] = 'changed'
        self.assertEqual(messages, before)

    def test_window_preserves_original_recent_order(self):
        messages = [
            {'role': 'system', 'content': 's'},
            {'role': 'user', 'content': 'm1'},
            {'role': 'assistant', 'content': 'm2'},
            {'role': 'user', 'content': 'm3'},
        ]
        result = fit_messages(messages, 3)
        self.assertEqual([row['content'] for row in result['window']], ['s', 'm2', 'm3'])
        self.assertEqual(result['dropped'], 1)


class InvalidInputTests(unittest.TestCase):
    def test_invalid_budget(self):
        with self.assertRaises(ConversationWindowError):
            fit_messages([], -1)
        with self.assertRaises(TypeError):
            fit_messages([], 1.5)
        with self.assertRaises(TypeError):
            fit_messages([], True)

    def test_messages_must_be_a_sequence(self):
        with self.assertRaises(TypeError):
            fit_messages({'role': 'user', 'content': 'x'}, 10)

    def test_invalid_message_entries(self):
        with self.assertRaises(ConversationWindowError):
            fit_messages(['not-a-mapping'], 10)
        with self.assertRaises(ConversationWindowError):
            fit_messages([{'role': 'user'}], 10)
        with self.assertRaises(TypeError):
            fit_messages([{'role': 'user', 'content': 1}], 10)
        with self.assertRaises(ConversationWindowError):
            fit_messages([{'role': 1, 'content': 'x'}], 10)


if __name__ == '__main__':
    unittest.main()
