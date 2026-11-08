"""作者：Wangyuan；日期：2026-11-08。职责：通过合成输入复验已确认缺陷。"""
import unittest
from datetime import datetime,timedelta,timezone
from planning import generate_schedule,allocate_resources
class ReleaseTests(unittest.TestCase):
 def test_deep_search_rejected_before_recursion(self) -> None:
  start=datetime(2030,1,1,tzinfo=timezone.utc);slots=[{'id':str(i),'start':(start+timedelta(days=i)).isoformat(),'end':(start+timedelta(days=i,hours=1)).isoformat()} for i in range(1100)]
  with self.assertRaisesRegex(ValueError,'200'):generate_schedule([{'id':'a'}],slots,minimum_rest_hours=0)
 def test_derived_nonfinite_score_rejected(self) -> None:
  with self.assertRaises(ValueError):allocate_resources([{'id':str(i),'features':{'x':1e308}} for i in range(2)],['a','b'],{'x':0},[],0)

 def test_demand_budget_checked_before_range_or_expansion(self) -> None:
  from unittest.mock import patch
  slot={'id':'a','start':'2030-01-01T00:00:00Z','end':'2030-01-01T01:00:00Z','needed':10**9}
  with patch('planning.range',side_effect=AssertionError('expanded before validation'),create=True):
   with self.assertRaisesRegex(ValueError,'200'):generate_schedule([{'id':'a'}],[slot],minimum_rest_hours=0)
