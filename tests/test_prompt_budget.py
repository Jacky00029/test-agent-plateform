import copy
import unittest

from agent_tools.prompt_budget import (
    PromptBudgetError,
    estimate_tokens,
    pack_prompt,
)


class EstimateTokensTests(unittest.TestCase):
    def test_empty_string_is_zero(self):
        self.assertEqual(estimate_tokens(''), 0)

    def test_non_empty_text_uses_ceiling_of_quarter_length(self):
        self.assertEqual(estimate_tokens('a'), 1)
        self.assertEqual(estimate_tokens('abcd'), 1)
        self.assertEqual(estimate_tokens('abcde'), 2)
        self.assertEqual(estimate_tokens('你'), 1)
        self.assertEqual(estimate_tokens('你好'), 1)
        self.assertEqual(estimate_tokens('你好啊'), 1)
        self.assertEqual(estimate_tokens('你好啊！'), 1)
        self.assertEqual(estimate_tokens('你好啊！?'), 2)

    def test_whitespace_is_not_empty(self):
        self.assertEqual(estimate_tokens(' '), 1)
        self.assertEqual(estimate_tokens('\n'), 1)

    def test_non_string_input_is_rejected(self):
        with self.assertRaises(TypeError):
            estimate_tokens(None)
        with self.assertRaises(TypeError):
            estimate_tokens(123)


class PackPromptTests(unittest.TestCase):
    def test_empty_segments(self):
        result = pack_prompt([], 10)
        self.assertEqual(result, {'segments': [], 'used_tokens': 0, 'dropped': []})

    def test_keeps_input_order_when_everything_fits(self):
        segments = [
            {'text': 'aaaa', 'priority': 0},
            {'text': 'bbbbbbbb', 'priority': 5},
            {'text': 'cccc', 'priority': -1},
        ]
        result = pack_prompt(segments, 10)
        self.assertEqual([row['text'] for row in result['segments']],
                         ['aaaa', 'bbbbbbbb', 'cccc'])
        self.assertEqual(result['used_tokens'], 4)
        self.assertLessEqual(result['used_tokens'], 10)
        self.assertEqual(result['dropped'], [])

    def test_skips_oversized_segment_and_fills_with_later_short_segment(self):
        segments = [
            {'text': 'x' * 12, 'priority': 0},
            {'text': 'y' * 8, 'priority': 0},
        ]
        result = pack_prompt(segments, 2)
        self.assertEqual([row['text'] for row in result['segments']], ['y' * 8])
        self.assertEqual(result['used_tokens'], 2)
        self.assertLessEqual(result['used_tokens'], 2)
        self.assertEqual([row['text'] for row in result['dropped']], ['x' * 12])

    def test_higher_priority_replaces_lower_priority_selection(self):
        segments = [
            {'text': 'l' * 8, 'priority': 0},
            {'text': 'h' * 4, 'priority': 10},
            {'text': 'm' * 4, 'priority': 1},
        ]
        result = pack_prompt(segments, 2)
        self.assertEqual([row['text'] for row in result['segments']], ['h' * 4, 'm' * 4])
        self.assertEqual(result['used_tokens'], 2)
        self.assertEqual([row['text'] for row in result['dropped']], ['l' * 8])

    def test_lower_priority_cannot_replace_selection(self):
        segments = [
            {'text': 'h' * 8, 'priority': 10},
            {'text': 'l' * 4, 'priority': 0},
        ]
        result = pack_prompt(segments, 2)
        self.assertEqual([row['text'] for row in result['segments']], ['h' * 8])
        self.assertEqual(result['used_tokens'], 2)
        self.assertEqual([row['text'] for row in result['dropped']], ['l' * 4])

    def test_zero_budget_drops_everything(self):
        segments = [{'text': 'data'}, {'text': ''}]
        result = pack_prompt(segments, 0)
        self.assertEqual(result['used_tokens'], 0)
        self.assertEqual([row['text'] for row in result['segments']], [''])
        self.assertEqual([row['text'] for row in result['dropped']], ['data'])

    def test_used_tokens_never_exceeds_budget(self):
        segments = [{'text': 'a' * size, 'priority': index % 3}
                    for index, size in enumerate([4, 16, 8, 32, 4, 12])]
        for budget in range(0, 20):
            result = pack_prompt(segments, budget)
            self.assertLessEqual(result['used_tokens'], budget)
            self.assertEqual(result['used_tokens'],
                             sum(estimate_tokens(row['text']) for row in result['segments']))

    def test_input_is_not_mutated_and_output_is_copied(self):
        segments = [
            {'text': 'aaaa', 'priority': 1, 'extra': {'k': 'v'}},
            {'text': 'bbbb', 'priority': 0},
        ]
        before = copy.deepcopy(segments)
        result = pack_prompt(segments, 10)
        self.assertEqual(segments, before)
        self.assertIsNot(result['segments'][0], segments[0])
        result['segments'][0]['text'] = 'changed'
        self.assertEqual(segments, before)

    def test_invalid_budget_is_rejected(self):
        with self.assertRaises(PromptBudgetError):
            pack_prompt([], -1)
        with self.assertRaises(TypeError):
            pack_prompt([], 1.5)
        with self.assertRaises(TypeError):
            pack_prompt([], True)

    def test_invalid_segment_is_rejected(self):
        with self.assertRaises(PromptBudgetError):
            pack_prompt(['not-a-mapping'], 10)
        with self.assertRaises(PromptBudgetError):
            pack_prompt([{'priority': 1}], 10)
        with self.assertRaises(TypeError):
            pack_prompt([{'text': 123}], 10)
        with self.assertRaises(PromptBudgetError):
            pack_prompt([{'text': 'x', 'priority': 'high'}], 10)

    def test_segments_must_be_sequence(self):
        with self.assertRaises(TypeError):
            pack_prompt({'text': 'x'}, 10)


if __name__ == '__main__':
    unittest.main()
