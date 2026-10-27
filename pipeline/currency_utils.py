"""
Currency and number parsing utilities for Indian business numbers.
Handles formats such as:
- '₹3.5 lakh' / 'Rs 3.5 lakh' / '3.5 lakhs' / 'Rs. 3.5 Lakh'
- '₹2 crore' / 'Rs 2 crore' / '2.5 Cr'
- '₹50,000' / 'Rs 50,000' / '50000'
- '₹15 thousand' / '15k'
"""
import re
from typing import Optional, Tuple


def parse_inr_string(text: str) -> Optional[int]:
    """
    Parses a string containing an Indian currency figure and returns an integer in INR.
    Returns None if no unambiguous number can be extracted.
    """
    if not text:
        return None

    cleaned = text.replace(",", "").strip()

    # Match Crore: e.g., 2.5 crore, Rs 2 crore, ₹ 10 Cr
    crore_match = re.search(r'(?:₹|rs\.?|inr)?\s*(-?\d+(?:\.\d+)?)\s*(?:crores?|cr\.?)\b', cleaned, re.IGNORECASE)
    if crore_match:
        val = float(crore_match.group(1))
        return int(val * 10000000)

    # Match Lakh: e.g., 3.5 lakh, Rs 50 lakhs, ₹ 5 Lac, 1.2 lacs
    lakh_match = re.search(r'(?:₹|rs\.?|inr)?\s*(-?\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?|lac|lk)\b', cleaned, re.IGNORECASE)
    if lakh_match:
        val = float(lakh_match.group(1))
        return int(val * 100000)

    # Match Thousand: e.g., 50 thousand, 50k
    thousand_match = re.search(r'(?:₹|rs\.?|inr)?\s*(-?\d+(?:\.\d+)?)\s*(?:thousands?|k)\b', cleaned, re.IGNORECASE)
    if thousand_match:
        val = float(thousand_match.group(1))
        return int(val * 1000)

    # Match direct currency figures: e.g., ₹50000, Rs. 50000, -50000
    direct_match = re.search(r'(?:(?:₹|rs\.?|inr)\s*)?(-?\d+)\b', cleaned, re.IGNORECASE)
    if direct_match:
        return int(direct_match.group(1))

    return None


def format_inr(amount: Optional[int]) -> str:
    """
    Formats an INR integer into human-readable Indian numbering system:
    e.g. 350000 -> '₹3.5 Lakh'
         20000000 -> '₹2 Crore'
         65000 -> '₹65,000'
    """
    if amount is None:
        return "Not found"

    is_negative = amount < 0
    abs_amt = abs(amount)

    prefix = "-₹" if is_negative else "₹"

    if abs_amt >= 10000000:
        cr = abs_amt / 10000000
        formatted = f"{cr:.2f}".rstrip("0").rstrip(".")
        return f"{prefix}{formatted} Crore"
    elif abs_amt >= 100000:
        lakh = abs_amt / 100000
        formatted = f"{lakh:.2f}".rstrip("0").rstrip(".")
        return f"{prefix}{formatted} Lakh"
    elif abs_amt >= 1000:
        # Standard Indian comma notation for thousands
        s = str(abs_amt)
        if len(s) <= 3:
            res = s
        else:
            last3 = s[-3:]
            remaining = s[:-3]
            # split remaining in pairs of 2 from right
            pairs = []
            while remaining:
                pairs.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            res = ",".join(pairs) + "," + last3
        return f"{prefix}{res}"
    else:
        return f"{prefix}{abs_amt}"
