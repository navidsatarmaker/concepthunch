import unittest
from pipeline.filter import evaluate_title_and_summary, has_likely_business_numbers


class TestFilters(unittest.TestCase):
    def test_positive_title_outcomes(self):
        cases = [
            ("Bengaluru quick-commerce startup shut down after severe cash crunch", "Operational details"),
            ("How a bootstrapped D2C brand clocked ₹50 crore revenue without VC money", "Founder interview"),
            ("Online grocery dark stores turned profitable in Gurgaon with unit economics", "Report"),
            ("Mumbai cloud kitchen network closed 15 outlets due to aggregator commissions", "Closure news"),
            ("Hardware venture reached break-even after 18 months of retail distribution", "Breakeven case study"),
            ("Setting up a tea kiosk requires initial investment of ₹3 lakh", "Setup guide and economics")
        ]
        for title, summary in cases:
            accepted, reason = evaluate_title_and_summary(title, summary)
            self.assertTrue(accepted, f"Failed for '{title}' - {reason}")

    def test_skip_funding_rounds(self):
        cases = [
            ("Fintech startup raises $25 million in Series B round", "Investment led by Tiger Global"),
            ("Edtech platform secures $5 mn seed funding to expand overseas", "Seed announcement"),
            ("Logistics SaaS bags $10M funding from existing investors", "Funding news"),
            ("EV battery maker closes Series A funding round", "Capital raise details")
        ]
        for title, summary in cases:
            accepted, reason = evaluate_title_and_summary(title, summary)
            self.assertFalse(accepted, f"Expected skip for '{title}' but was accepted")
            self.assertIn("funding/partnership/launch", reason)

    def test_skip_partnerships_and_launches(self):
        cases = [
            ("Zomato partners with local restaurants for festival deals", "Partnership agreement"),
            ("Tech giant launches new AI tool for creators", "New product debut"),
            ("Retail brand appoints new Chief Operating Officer", "Executive leadership update")
        ]
        for title, summary in cases:
            accepted, reason = evaluate_title_and_summary(title, summary)
            self.assertFalse(accepted, f"Expected skip for '{title}' but was accepted")


if __name__ == "__main__":
    unittest.main()
