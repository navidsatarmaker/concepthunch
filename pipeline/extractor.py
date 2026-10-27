"""
Gemini Extractor module.
Uses google-genai library to extract structured business cases.
Prompt enforces strict JSON output, verbatim quotes under 25 words,
and null for unmentioned fields.
"""

import os
import json
import re
from typing import Optional, Dict, Any

EXTRACTION_SYSTEM_PROMPT = """You are a rigorous, neutral business data extraction engine.
Analyze the provided article text about an Indian business venture and extract factual data into STRICT JSON format.

RULES:
1. Use ONLY facts explicitly stated in the article text. Never infer, estimate, or make up any value.
2. If any fact or number is not stated or ambiguous, set it to null.
3. Every extracted number MUST have a matching `_quote` containing the EXACT supporting sentence from the text (under 25 words).
4. `own_summary` must be 2-3 neutral sentences in your own words summarizing what happened. Never copy article text directly.
5. `what_worked` and `what_failed` must only contain concrete factors cited in the text.
6. `status` must be one of: "running", "shut_down", "acquired", or "unknown".
7. DO NOT use advising or recommending language ("you should", "best business").
8. Output ONLY a valid JSON object matching the schema below. No markdown backticks, no explanations.

JSON SCHEMA:
{
  "business_name": "string",
  "business_type": "string (slug matching the category e.g. tea-cafe, cloud-kitchen, ev-charging-station, direct-to-consumer-apparel, logistics-fleet, etc.)",
  "city": "string or null",
  "state": "string or null",
  "year_started": int or null,
  "status": "running | shut_down | acquired | unknown",
  "capital_invested_inr": int or null,
  "capital_invested_inr_quote": "exact sentence under 25 words or null",
  "monthly_cost_inr": int or null,
  "monthly_cost_inr_quote": "exact sentence under 25 words or null",
  "revenue_inr": int or null,
  "revenue_period": "monthly | annual | null",
  "revenue_inr_quote": "exact sentence under 25 words or null",
  "profit_or_loss_inr": int or null,
  "profit_or_loss_inr_quote": "exact sentence under 25 words or null",
  "time_to_breakeven_months": int or null,
  "time_to_breakeven_months_quote": "exact sentence under 25 words or null",
  "what_worked": ["string"],
  "what_failed": ["string"],
  "own_summary": "2-3 neutral sentences"
}
"""


def extract_with_gemini(article_text: str, model_name: str) -> Optional[Dict[str, Any]]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set.")
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"{EXTRACTION_SYSTEM_PROMPT}\n\nARTICLE TEXT:\n{article_text[:12000]}"
        
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        text = response.text.strip()
        # Clean json backticks if any
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'```$', '', text).strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gemini extraction error: {e}")
        return None
