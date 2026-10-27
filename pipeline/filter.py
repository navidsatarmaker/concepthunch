"""
Keyword filter module.
Provides:
1. Fast title & RSS summary filter to screen candidate articles BEFORE fetching page content.
   - Requires business outcome signals (shut down, bootstrapped, profitable, revenue, turnover, loss,
     unit economics, closed, scaled, break-even, cost to set up, investment of ₹/Rs).
   - Skips pure funding rounds, partnerships, and product launches.
2. Content-level keyword filter for full article text before LLM extraction.
"""

import re
from typing import Tuple, Optional

# Positive indicators of real operational business outcomes and metrics
OUTCOME_PATTERNS = [
    r'\bshut(?:ting)?\s*down\b',
    r'\bclosed\b',
    r'\bclosure\b',
    r'\bwound\s*up\b',
    r'\bbootstrapp(?:ed|ing)\b',
    r'\bprofitab(?:le|ility)\b',
    r'\brevenue\b',
    r'\bturnover\b',
    r'\bloss(?:es)?\b',
    r'\bunit\s*economics\b',
    r'\bscaled\b',
    r'\bbreak-?even\b',
    r'\bcost\s*to\s*set\s*up\b',
    r'\bsetup\s*cost\b',
    r'\binitial\s*investment\b',
    r'\bcapital\s*invested\b',
    r'\bmonthly\s*(?:cost|burn|expenses?)\b',
    r'\binvestment\s*of\s*(?:₹|rs\.?|inr|\d)',
    r'(?:₹|rs\.?|inr)\s*\d+(?:\.\d+)?\s*(?:crore|cr|lakh|lac|k)\s*(?:revenue|profit|loss|turnover|investment)',
    r'\boperating\s*profit\b',
    r'\bnet\s*loss\b'
]

# Negative indicators for pure funding rounds, partnerships, and product launches
SKIP_PATTERNS = [
    r'\braises?\s*(?:\$|usd|mn|million|series|\d)',
    r'\bsecures?\s*(?:\$|usd|funding|seed|series|\d)',
    r'\bbag(?:s|ged)?\s*(?:\$|usd|\d+\s*mn|\d+\s*million|funding)',
    r'\bfunding\s*round\b',
    r'\bseries\s*[a-j]\b',
    r'\bseed\s*round\b',
    r'\bpartner(?:s|ed|ship)\s*with\b',
    r'\bteams?\s*up\s*with\b',
    r'\blaunche(?:s|d)?\s*new\b',
    r'\bunveils?\b',
    r'\bintroduces?\s*new\b',
    r'\bappoints?\b',
    r'\bhiring\b'
]

COMPILED_OUTCOME_PATTERNS = [re.compile(p, re.IGNORECASE) for p in OUTCOME_PATTERNS]
COMPILED_SKIP_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SKIP_PATTERNS]


def evaluate_title_and_summary(title: str, summary: str = "") -> Tuple[bool, str]:
    """
    Evaluates article title and summary before fetching the webpage.
    Returns:
        (is_accepted, reason)
    """
    combined = f"{title} {summary}".strip()
    if not combined:
        return False, "Empty title and summary"

    # 1. Check for pure funding/partnership/launch noise
    for p in COMPILED_SKIP_PATTERNS:
        match = p.search(combined)
        if match:
            return False, f"Matched skip pattern (funding/partnership/launch): '{match.group(0)}'"

    # 2. Check for positive business outcome keywords
    for p in COMPILED_OUTCOME_PATTERNS:
        match = p.search(combined)
        if match:
            return True, f"Matched outcome pattern: '{match.group(0)}'"

    return False, "No business outcome indicators in title or summary"


# Financial keywords for full article body checks
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
    Checks if an article body has at least `min_matches` financial indicators.
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
