import unittest
from build_monthly_report import (
    compute_monthly_report_data,
    verify_ai_note_numbers,
    check_forbidden_words
)


class TestMonthlyReport(unittest.TestCase):
    def test_ranking_threshold_five_cases(self):
        # 1 type with 5 cases (should be ranked)
        # 1 type with 2 cases (should be emerging)
        business_types = [
            {"slug": "tea-cafe", "name": "Tea Cafe", "description": "Tea cafe"},
            {"slug": "cloud-kitchen", "name": "Cloud Kitchen", "description": "Cloud kitchen"}
        ]
        cases = [
            {"business_type": "tea-cafe", "capital_invested_inr": 300000, "status": "running"},
            {"business_type": "tea-cafe", "capital_invested_inr": 350000, "status": "running"},
            {"business_type": "tea-cafe", "capital_invested_inr": 400000, "status": "running"},
            {"business_type": "tea-cafe", "capital_invested_inr": 500000, "status": "shut_down"},
            {"business_type": "tea-cafe", "capital_invested_inr": 450000, "status": "shut_down"},
            {"business_type": "cloud-kitchen", "capital_invested_inr": 600000, "status": "running"},
            {"business_type": "cloud-kitchen", "capital_invested_inr": 700000, "status": "shut_down"},
        ]

        report = compute_monthly_report_data(cases, business_types, "2026-10")
        self.assertEqual(len(report["ranked_types"]), 1)
        self.assertEqual(report["ranked_types"][0]["slug"], "tea-cafe")
        self.assertEqual(len(report["emerging_types"]), 1)
        self.assertEqual(report["emerging_types"][0]["slug"], "cloud-kitchen")

    def test_verify_ai_note_numbers_success(self):
        # Stats input has 5 cases and median 3.5 lakh (350000)
        input_numbers = [5.0, 350000.0, 3.5]
        note = "The research documented 5 verified tea cafe cases with median capital of 3.5 lakh."
        self.assertTrue(verify_ai_note_numbers(note, input_numbers))

    def test_verify_ai_note_numbers_failure_on_unsupported_figure(self):
        input_numbers = [5.0, 350000.0]
        # Note introduces invented 85% success rate or 12 months breakeven
        note = "The research found an 85% success rate across the 5 cases."
        self.assertFalse(verify_ai_note_numbers(note, input_numbers))

    def test_check_forbidden_words(self):
        clean_text = "What happened was that operating costs exceeded monthly revenues."
        self.assertEqual(len(check_forbidden_words(clean_text)), 0)

        violating_text = "If you want to make money, you should start this best business."
        violations = check_forbidden_words(violating_text)
        self.assertTrue(len(violations) >= 2)


if __name__ == "__main__":
    unittest.main()
