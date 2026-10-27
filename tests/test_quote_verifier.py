import unittest
from pipeline.quote_verifier import verify_numeric_field, verify_case_quotes


class TestQuoteVerifier(unittest.TestCase):
    def test_quote_exact_match_success(self):
        article = "The founders started the outlet with an initial investment of Rs 3.5 lakh in late 2018."
        quote = "The founders started the outlet with an initial investment of Rs 3.5 lakh"
        val, q, reason = verify_numeric_field(article, "capital_invested_inr", 350000, quote)
        self.assertEqual(val, 350000)
        self.assertEqual(q, quote)
        self.assertEqual(reason, "verified")

    def test_quote_not_in_article(self):
        article = "The enterprise operated with basic equipment."
        quote = "The founders invested Rs 5 lakh"
        val, q, reason = verify_numeric_field(article, "capital_invested_inr", 500000, quote)
        self.assertIsNone(val)
        self.assertIsNone(q)
        self.assertIn("not found verbatim", reason)

    def test_quote_exceeds_word_count(self):
        article = "The founders started the outlet with an initial investment of Rs 3.5 lakh after spending several months researching locations across the entire state and meeting dozens of potential suppliers and contractors."
        quote = "The founders started the outlet with an initial investment of Rs 3.5 lakh after spending several months researching locations across the entire state and meeting dozens of potential suppliers and contractors"
        val, q, reason = verify_numeric_field(article, "capital_invested_inr", 350000, quote)
        self.assertIsNone(val)
        self.assertIsNone(q)
        self.assertIn("exceeds 25 words", reason)

    def test_quote_number_mismatch(self):
        article = "The founders spent Rs 50,000 on furniture."
        quote = "The founders spent Rs 50,000 on furniture."
        val, q, reason = verify_numeric_field(article, "capital_invested_inr", 500000, quote)
        self.assertIsNone(val)
        self.assertIsNone(q)
        self.assertIn("does not match figure", reason)


if __name__ == "__main__":
    unittest.main()
