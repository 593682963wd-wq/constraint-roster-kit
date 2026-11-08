"""作者：Wangyuan；日期：2026-10-29；职责：仅以从零合成输入验证核心与异常路径。"""

import unittest
from planning import *
class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.people=[{'id':'p1','skills':['q'],'max_assignments':1},{'id':'p2','skills':['q'],'max_assignments':1}]
        self.slots=[{'id':'s1','start':'2030-01-01T08:00:00+00:00','end':'2030-01-01T12:00:00+00:00','skills':['q']},{'id':'s2','start':'2030-01-01T11:00:00+00:00','end':'2030-01-01T15:00:00+00:00','skills':['q']}]
    def test_complete_roster_and_month_counts(self):
        result=generate_schedule(self.people,self.slots,minimum_rest_hours=10)
        self.assertEqual(result['status'],'complete'); self.assertEqual(result['issues'],[])
        self.assertEqual(sum(x['count'] for x in monthly_counts(result['assignments'],self.slots,'2030-01')),2)
    def test_impossible_and_budget_are_reported(self):
        result=generate_schedule(self.people[:1],self.slots,minimum_rest_hours=10)
        self.assertEqual(result['status'],'infeasible')
        result=generate_schedule(self.people,self.slots,minimum_rest_hours=10,budget=1)
        self.assertEqual(result['status'],'budget_exhausted')
    def test_qualification_availability_and_overlap(self):
        people=[{'id':'p1','skills':[],'unavailable':[{'start':'2030-01-01T00:00:00+00:00','end':'2030-01-02T00:00:00+00:00'}]}]
        issues=validate_schedule([{'person':'p1','slot':'s1'},{'person':'p1','slot':'s2'}],people,self.slots)
        self.assertTrue({'qualification','unavailable','rest_or_overlap'} <= {x['kind'] for x in issues})
    def test_duplicates_and_naive_dates_rejected(self):
        with self.assertRaises(ValueError): monthly_counts([{'person':'p1','slot':'s1'}]*2,self.slots,'2030-01')
        with self.assertRaises(ValueError): stamp('2030-01-01T00:00:00')
        with self.assertRaises(ValueError): generate_schedule(self.people*2,self.slots,minimum_rest_hours=0)
    def test_feature_allocation_balances_and_explains(self):
        result=allocate_resources([{'id':'a','features':{'work':2}},{'id':'b','features':{'work':2}}],['x','y'],{'work':1},[['a','b']],10)
        self.assertEqual(result['result']['score'],0); self.assertTrue(result['optimal']); self.assertEqual(result['result']['conflicts'],0)
    def test_invalid_weights_and_limited_search(self):
        with self.assertRaises(ValueError): allocate_resources([],['x','y'],{'work':float('nan')},[],0)
        result=allocate_resources([{'id':'a','features':{'work':1}}],['x','y'],{'work':1},[],0,budget=1)
        self.assertFalse(result['optimal'])
    def test_duration_margin_and_overlap(self):
        self.assertEqual(duration_margin(self.slots[:1],300)['margin_minutes'],60)
        with self.assertRaises(ValueError): duration_margin(self.slots,300)
        self.assertEqual(duration_margin([],0)['status'],'missing')
    def test_xlsx_export_roundtrip(self):
        import tempfile
        from pathlib import Path
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'roster.xlsx'; export_xlsx([{'person':'p1','slot':'s1'}],str(path)); book=load_workbook(path)
            self.assertEqual(book.active['A2'].value,'p1'); self.assertEqual(book.active['B2'].value,'s1'); book.close()
    def test_contiguous_days_do_not_bridge_gap(self):
        self.assertEqual(contiguous_days(['2030-01-04','2030-01-01','2030-01-02']),[['2030-01-01','2030-01-02'],['2030-01-04']])

if __name__ == "__main__":
    unittest.main()
