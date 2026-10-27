import unittest
from pipeline.currency_utils import parse_inr_string, format_inr


class TestCurrencyUtils(unittest.TestCase):
    def test_parse_crore(self):
        self.assertEqual(parse_inr_string("₹2 crore"), 20000000)
        self.assertEqual(parse_inr_string("Rs. 1.5 Crore"), 15000000)
        self.assertEqual(parse_inr_string("10 cr"), 100000000)

    def test_parse_lakh(self):
        self.assertEqual(parse_inr_string("₹50 lakh"), 5000000)
        self.assertEqual(parse_inr_string("Rs 3.5 lakhs"), 350000)
        self.assertEqual(parse_inr_string("2.8 Lacs"), 280000)
        self.assertEqual(parse_inr_string("1 lac"), 100000)

    def test_parse_thousand(self):
        self.assertEqual(parse_inr_string("₹50 thousand"), 50000)
        self.assertEqual(parse_inr_string("65k"), 65000)

    def test_parse_direct_numbers(self):
        self.assertEqual(parse_inr_string("₹50,000"), 50000)
        self.assertEqual(parse_inr_string("Rs 1,80,000"), 180000)
        self.assertEqual(parse_inr_string("-50,000"), -50000)

    def test_format_inr(self):
        self.assertEqual(format_inr(None), "Not found")
        self.assertEqual(format_inr(20000000), "₹2 Crore")
        self.assertEqual(format_inr(350000), "₹3.5 Lakh")
        self.assertEqual(format_inr(65000), "₹65,000")
        self.assertEqual(format_inr(-180000), "-₹1.8 Lakh")


if __name__ == "__main__":
    unittest.main()
