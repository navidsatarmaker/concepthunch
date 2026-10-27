"""
Cheap keyword filter module.
Filters out articles that do not mention numbers, financial terms, or business economics,
conserving free API quota before invoking Gemini.
"""

import re

# Keywords indicating presence of business financials in India
FINANCIAL_KEYWORDS = [
    r'\b(?:₹|rs\.?|inr)\b',
    r'\b(?:crore|crores|cr)\b',
    r'\b(?:lakh|lakhs|lac|lacs)\b',
    r'\bcapital\b',
    r'\binvestment\b',
    r'\brevenue\b',
    r'\bturnover\b',
    r'\bprofit\b',
    r'\bloss\b',
    r'\bbreakeven\b',
    r'\bmonthly cost\b',
    r'\brun rate\b'
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FINANCIAL_KEYWORDS]


def has_likely_business_numbers(text: str, min_matches: int = 2) -> bool:
    """
    Checks if an article has at least `min_matches` financial indicators.
    """
    if not text:
        return False

    matches = 0
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            matches += 1
            if matches >= min_matches:
                return True

    return False
