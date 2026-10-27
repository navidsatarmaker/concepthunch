import unittest
from build_site import compute_summary_for_type


class TestSummaries(unittest.TestCase):
    def test_fewer_than_three_cases_threshold(self):
        cases = [
            {
                "business_type": "tea-cafe",
                "capital_invested_inr": 300000,
                "monthly_cost_inr": 50000,
                "revenue_inr": 1000000,
                "time_to_breakeven_months": 12,
                "status": "running",
                "what_failed": ["High rent"]
            },
            {
                "business_type": "tea-cafe",
                "capital_invested_inr": 400000,
                "monthly_cost_inr": 60000,
                "revenue_inr": 1200000,
                "time_to_breakeven_months": 14,
                "status": "shut_down",
                "what_failed": ["High rent", "Staff turnover"]
            }
        ]
        summary = compute_summary_for_type("tea-cafe", cases)
        self.assertEqual(summary["case_count"], 2)
        self.assertFalse(summary["has_sufficient_data"])

    def test_three_or_more_cases_threshold_and_calculations(self):
        cases = [
            {"business_type": "tea-cafe", "capital_invested_inr": 200000, "status": "running", "what_failed": ["High rent"]},
            {"business_type": "tea-cafe", "capital_invested_inr": 300000, "status": "running", "what_failed": ["High rent"]},
            {"business_type": "tea-cafe", "capital_invested_inr": 500000, "status": "shut_down", "what_failed": ["Competition"]}
        ]
        summary = compute_summary_for_type("tea-cafe", cases)
        self.assertEqual(summary["case_count"], 3)
        self.assertTrue(summary["has_sufficient_data"])
        self.assertEqual(summary["capital_invested_inr"]["min"], 200000)
        self.assertEqual(summary["capital_invested_inr"]["median"], 300000)
        self.assertEqual(summary["capital_invested_inr"]["max"], 500000)
        self.assertEqual(summary["common_failure_reasons"], ["High rent"])


if __name__ == "__main__":
    unittest.main()
