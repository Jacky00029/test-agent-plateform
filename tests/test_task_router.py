import unittest

from agent_tools.task_router import GENERAL, TaskRouter, TaskRouterError


class RankingTests(unittest.TestCase):
    def test_more_keyword_hits_wins(self):
        router = TaskRouter()
        router.register('broad', ['python', 'bug', 'api'], priority=0)
        router.register('narrow', ['python', 'bug'], priority=100)
        self.assertEqual(router.route('python bug api'), 'broad')

    def test_priority_breaks_tie_on_hit_count(self):
        router = TaskRouter()
        router.register('low', ['python', 'bug'], priority=1)
        router.register('high', ['python', 'bug'], priority=5)
        self.assertEqual(router.route('python bug'), 'high')

    def test_matching_ignores_case(self):
        router = TaskRouter()
        router.register('code', ['Python', 'BUG'], priority=0)
        self.assertEqual(router.route('PYTHON and bug'), 'code')
        self.assertEqual(router.route('python and Bug'), 'code')

    def test_combined_ranking(self):
        router = TaskRouter()
        router.register('three-low', ['a', 'b', 'c'], priority=1)
        router.register('two-high', ['a', 'b'], priority=9)
        router.register('three-high', ['a', 'b', 'c'], priority=5)
        self.assertEqual(router.route('a b c'), 'three-high')

    def test_repeated_keyword_in_text_counts_once(self):
        router = TaskRouter()
        router.register('single', ['bug'], priority=0)
        router.register('double', ['bug', 'python'], priority=0)
        self.assertEqual(router.route('bug bug bug'), 'single')

    def test_chinese_keywords(self):
        router = TaskRouter()
        router.register('code', ['代码', '报错'], priority=0)
        router.register('docs', ['文档'], priority=0)
        self.assertEqual(router.route('请帮我检查代码，为什么报错'), 'code')
        self.assertEqual(router.route('补充一下文档'), 'docs')


class TieAndFallbackTests(unittest.TestCase):
    def test_same_hits_and_priority_keep_registration_order(self):
        router = TaskRouter()
        router.register('first', ['python'], priority=3)
        router.register('second', ['python'], priority=3)
        self.assertEqual(router.route('python'), 'first')

    def test_rules_constructor_preserves_order(self):
        router = TaskRouter([
            {'name': 'first', 'keywords': ['x'], 'priority': 1},
            {'name': 'second', 'keywords': ['x'], 'priority': 1},
        ])
        self.assertEqual(router.route('x'), 'first')

    def test_no_match_returns_general(self):
        router = TaskRouter()
        router.register('code', ['python'], priority=10)
        self.assertEqual(router.route('请写一首诗'), GENERAL)
        self.assertEqual(router.route(''), GENERAL)

    def test_empty_router_returns_general(self):
        self.assertEqual(TaskRouter().route('anything'), GENERAL)

    def test_rules_property_is_a_defensive_copy(self):
        router = TaskRouter()
        router.register('code', ['python'], priority=1)
        snapshot = router.rules
        snapshot[0]['keywords'].append('java')
        snapshot[0]['name'] = 'changed'
        self.assertEqual(router.route('java'), GENERAL)
        self.assertEqual(router.rules[0]['name'], 'code')


class RegistrationTests(unittest.TestCase):
    def test_invalid_names(self):
        for name in ('', '   ', None, 1):
            with self.assertRaises(TaskRouterError):
                TaskRouter().register(name, ['x'])
        router = TaskRouter().register('code', ['x'])
        with self.assertRaises(TaskRouterError):
            router.register('code', ['y'])

    def test_invalid_keywords(self):
        for keywords in (None, 'python', [], ('ok', ''), ['x', 'X'], [1], ['   ']):
            with self.assertRaises(TaskRouterError):
                TaskRouter().register('code', keywords)

    def test_invalid_priority(self):
        for priority in (True, 1.5, 'high', None):
            with self.assertRaises(TaskRouterError):
                TaskRouter().register('code', ['x'], priority=priority)

    def test_invalid_rule_mapping(self):
        with self.assertRaises(TaskRouterError):
            TaskRouter(['not-a-rule'])

    def test_route_requires_text(self):
        with self.assertRaises(TypeError):
            TaskRouter().route(None)

    def test_register_is_chainable(self):
        router = TaskRouter().register('a', ['x']).register('b', ['y'])
        self.assertEqual(router.route('y'), 'b')


if __name__ == '__main__':
    unittest.main()
