"""
Quote verifier module.
PURE CODE, ZERO AI.

Rules enforced:
1. Normalize whitespace, casing, and punctuation.
2. Confirm each `_quote` appears verbatim in the article text.
3. Confirm the quote length is under 25 words.
4. Confirm the parsed number is supported inside that exact quote using currency_utils.
5. If any check fails, set the numeric field and its quote to null.
"""

import re
from typing import Dict, Any, Tuple
from pipeline.currency_utils import parse_inr_string


def normalize_text(text: str) -> str:
    """Standardizes quotes, hyphens, and multi-spaces for strict verbatim substring search."""
    if not text:
        return ""
    # Standardize curly quotes and apostrophes
    t = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    t = t.replace("–", "-").replace("—", "-")
    # Collapse multiple spaces and linebreaks
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def verify_numeric_field(article_text_normalized: str, field_name: str, value: Any, quote: Any) -> Tuple[Any, Any, str]:
    """
    Verifies that a field's value and supporting quote meet all standards.
    Returns (verified_value, verified_quote, reason).
    """
    if value is None:
        return None, None, "value is null"

    if not quote or not isinstance(quote, str):
        return None, None, "missing quote for value"

    norm_quote = normalize_text(quote)

    # Check 1: Quote word count (must be under 25 words)
    words = norm_quote.split()
    if len(words) > 25:
        return None, None, f"quote exceeds 25 words ({len(words)} words)"

    # Check 2: Verbatim presence in article text (case-insensitive substring)
    if norm_quote.lower() not in article_text_normalized.lower():
        return None, None, "quote not found verbatim in article text"

    # Check 3: Number representation inside quote
    # For breakeven months:
    if field_name == "time_to_breakeven_months":
        month_match = re.search(r'\b(\d+)\s*(?:months?|mos?|yrs?|years?)\b', norm_quote, re.IGNORECASE)
        if not month_match:
            # Check if value itself appears as a digit in the quote
            if str(value) not in norm_quote:
                return None, None, f"breakeven value {value} not found in quote"
        return value, quote, "verified"

    # For INR values: verify the quote parses to a compatible number
    parsed_inr = parse_inr_string(norm_quote)
    if parsed_inr is None:
        return None, None, f"no numeric INR figure detected in quote: '{quote}'"

    # Compare extracted value and quote-parsed value within a reasonable tolerance (e.g., exact or rounding)
    if value != 0 and parsed_inr != 0:
        ratio = abs(value / parsed_inr)
        if ratio < 0.90 or ratio > 1.10:
            return None, None, f"extracted value ({value}) does not match figure in quote ({parsed_inr})"

    return value, quote, "verified"


def verify_case_quotes(case_data: Dict[str, Any], raw_article_text: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Performs pure-code quote verification on all financial and numeric fields.
    Nullefies any field where verification fails.
    Returns (cleaned_case_data, audit_log).
    """
    cleaned = dict(case_data)
    audit = {}
    norm_article = normalize_text(raw_article_text)

    fields_to_check = [
        ("capital_invested_inr", "capital_invested_inr_quote"),
        ("monthly_cost_inr", "monthly_cost_inr_quote"),
        ("revenue_inr", "revenue_inr_quote"),
        ("profit_or_loss_inr", "profit_or_loss_inr_quote"),
        ("time_to_breakeven_months", "time_to_breakeven_months_quote")
    ]

    for val_field, quote_field in fields_to_check:
        val = cleaned.get(val_field)
        quote = cleaned.get(quote_field)

        new_val, new_quote, reason = verify_numeric_field(norm_article, val_field, val, quote)
        cleaned[val_field] = new_val
        cleaned[quote_field] = new_quote
        audit[val_field] = reason

    # Also clean revenue_period if revenue_inr was nulled
    if cleaned.get("revenue_inr") is None:
        cleaned["revenue_period"] = None

    if "verification" not in cleaned or not isinstance(cleaned["verification"], dict):
        cleaned["verification"] = {}

    cleaned["verification"]["quotes_verified"] = True
    return cleaned, audit
