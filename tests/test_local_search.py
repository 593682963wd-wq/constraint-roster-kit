"""作者：Wangyuan；日期：2026-10-29。职责：有界局部搜索回归。"""
import unittest
from planning import allocate_resources


class LocalSearchTests(unittest.TestCase):
    def test_seed_constraints_budget_and_score(self):
        items = [{'id':str(i),'features':{'load':1}} for i in range(8)]
        items[0]['fixed_group'] = 'B'
        items[1]['allowed_groups'] = ['A']
        args = (items, ['A','B'], {'load':1}, [], 0)
        result = allocate_resources(*args, method='local', seed=7, budget=40)
        self.assertEqual(result, allocate_resources(*args, method='local', seed=7, budget=40))
        self.assertEqual(result['result']['assignment']['0'], 'B')
        self.assertEqual(result['result']['assignment']['1'], 'A')
        self.assertLessEqual(result['examined'], 40)
        self.assertFalse(result['optimal'])
        self.assertEqual(result['result']['score'], 0)

    def test_one_evaluation_and_invalid_constraint(self):
        items = [{'id':'sample','features':{'load':1},'allowed_groups':['B']}]
        result = allocate_resources(items,['A','B'],{'load':1},[],0,method='local',budget=1)
        self.assertEqual(result['examined'], 1)
        self.assertEqual(result['status'],'budget_exhausted')
        items[0]['fixed_group'] = 'A'
        with self.assertRaises(ValueError): allocate_resources(items,['A','B'],{'load':1},[],0)


if __name__ == '__main__': unittest.main()
