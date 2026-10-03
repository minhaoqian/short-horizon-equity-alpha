"""Timing and coverage controls; no targets are frozen by these tests."""
import csv
from datetime import date
from pathlib import Path
import unittest
from src.data.target_boundary_qa import entitled_at_ex_date, planned_dates


class BoundaryTests(unittest.TestCase):
    def test_entry_ex_date_is_excluded(self):
        self.assertFalse(entitled_at_ex_date(date(2020,1,2),date(2020,1,9),date(2020,1,2)))

    def test_exit_ex_date_is_included(self):
        self.assertTrue(entitled_at_ex_date(date(2020,1,2),date(2020,1,9),date(2020,1,9)))

    def test_outside_boundary_is_excluded(self):
        for x in [date(2020,1,1),date(2020,1,10)]:
            self.assertFalse(entitled_at_ex_date(date(2020,1,2),date(2020,1,9),x))

    def test_global_calendar_handles_weekend_and_missing_security_row(self):
        cal=[date(2020,1,2),date(2020,1,3),date(2020,1,6),date(2020,1,7),date(2020,1,8),date(2020,1,9),date(2020,1,10)]
        self.assertEqual(planned_dates(cal,0),(date(2020,1,3),date(2020,1,10)))
        self.assertEqual(planned_dates(cal,1),(date(2020,1,6),None))
        self.assertEqual(planned_dates(cal,6),(None,None))

    def test_local_audit_partition_and_endpoint_identity(self):
        p=Path(__file__).resolve().parents[1]/'results/tables/stage1g'
        if not (p/'target_boundary_counts.csv').exists():
            self.skipTest('Local licensed-data audit outputs are absent')
        with (p/'target_boundary_counts.csv').open() as f:
            counts={r['category']:int(r['observations']) for r in csv.DictReader(f)}
        with (p/'target_boundary_primary_paths.csv').open() as f:
            paths=list(csv.DictReader(f))
        self.assertEqual(sum(int(r['observations']) for r in paths),6699101)
        self.assertEqual(counts['missing_exit_all_non_censored'],counts['both_missing_non_censored']+counts['missing_exit_given_entry'])
        self.assertEqual(counts['daily_delist_flag_1_6'],counts['entry_delist_flag']+counts['interior_delist_flag']+counts['exit_delist_flag'])
        self.assertGreater(counts['ordinary_any_1_6'],counts['ordinary_entitlement_2_6_proxy'])

if __name__=='__main__':unittest.main()
