"""
Groq Cross-Checker module.
Uses a secondary free-tier LLM (via Groq API) to independently review
whether the extracted fields are accurately grounded in the source text.
Any field flagged as unsupported is set to null.
"""

import os
import json
import re
from typing import Dict, Any, Tuple

CROSS_CHECK_PROMPT = """You are a strict data validation auditor.
You will be given the original ARTICLE TEXT and an EXTRACTED JSON representing a business case.
Your task is to determine whether each extracted field is strictly supported by the text.

ARTICLE TEXT:
{article_text}

EXTRACTED CASE DATA:
{case_json}

Return a STRICT JSON object indicating true (supported) or false (unsupported/hallucinated) for each field:
{{
  "capital_invested_inr": true/false,
  "monthly_cost_inr": true/false,
  "revenue_inr": true/false,
  "profit_or_loss_inr": true/false,
  "time_to_breakeven_months": true/false,
  "status": true/false,
  "what_worked": true/false,
  "what_failed": true/false
}}
Output ONLY valid JSON.
"""


def cross_check_with_groq(article_text: str, case_data: Dict[str, Any], model_name: str) -> Tuple[Dict[str, Any], Dict[str, bool]]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not set. Skipping secondary Groq cross-check.")
        case_data.setdefault("verification", {})["cross_checked"] = False
        return case_data, {}

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        prompt = CROSS_CHECK_PROMPT.format(
            article_text=article_text[:10000],
            case_json=json.dumps(case_data, indent=2)
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a factual audit engine outputting JSON only."},
                {"role": "user", "content": prompt}
            ],
            model=model_name,
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        resp_text = chat_completion.choices[0].message.content.strip()
        checks = json.loads(resp_text)

        cleaned = dict(case_data)
        for field, is_supported in checks.items():
            if not is_supported:
                print(f"Groq flagged {field} as unsupported. Nulling field.")
                if field in cleaned:
                    cleaned[field] = None
                    quote_field = f"{field}_quote"
                    if quote_field in cleaned:
                        cleaned[quote_field] = None

        cleaned.setdefault("verification", {})["cross_checked"] = True
        return cleaned, checks
    except Exception as e:
        print(f"Groq cross-check error: {e}")
        case_data.setdefault("verification", {})["cross_checked"] = False
        return case_data, {}
