"""作者：Wangyuan；日期：2026-10-29。职责：独立复核中的搜索预算与日历口径回归。"""
import unittest
from planning import allocate_resources, validate_schedule, monthly_counts


class ReviewTests(unittest.TestCase):
    def test_budget_is_not_proof_of_infeasibility(self):
        items = [{'id': 'one', 'features': {}, 'allowed_groups': ['B']}]
        self.assertEqual(allocate_resources(items, ['A', 'B'], {}, [], 0, budget=1)['status'], 'budget_exhausted')
        self.assertEqual(allocate_resources(items, ['A', 'B'], {}, [], 0, budget=2)['status'], 'complete')

    def test_business_day_and_month_share_explicit_timezone(self):
        people = [{'id': 'person', 'max_consecutive_days': 1}]
        slots = [{'id': 'a', 'start': '2030-01-01T01:00:00+08:00', 'end': '2030-01-01T02:00:00+08:00'},
                 {'id': 'b', 'start': '2030-01-02T23:00:00+08:00', 'end': '2030-01-03T00:00:00+08:00'}]
        rows = [{'person': 'person', 'slot': name} for name in ['a', 'b']]
        self.assertTrue(any(x['kind'] == 'consecutive_days' for x in validate_schedule(rows, people, slots, calendar_timezone='Asia/Shanghai')))
        self.assertEqual(monthly_counts(rows, slots, '2030-01', calendar_timezone='Asia/Shanghai')[0]['count'], 2)
        self.assertEqual(monthly_counts(rows, slots, '2030-01', calendar_timezone='UTC')[0]['count'], 1)


if __name__ == '__main__': unittest.main()
