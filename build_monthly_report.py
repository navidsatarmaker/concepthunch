"""
Monthly Ideas Report Builder.
Generates monthly evidence-based reports published at /ideas/<YYYY-MM>/ with archive at /ideas/.
Executed on the 1st of every month via GitHub Actions cron or manual dispatch.

Rules:
- All rankings and numbers computed by CODE from data/cases/ and data/summaries/. AI never invents or estimates any figure.
- Neutral wording only. Heading: 'What the research shows this month'.
- Every ranked item links to its business type page and individual cases.
- Every list shows case_count.
- A business type is RANKED only if it has >= 5 verified cases.
  With 1-4 cases it goes under 'Emerging (early signal, too few cases)' and is never ranked.
- Mandatory note: 'Based on cases reported by news and public records. Cases that were never reported are not counted, so this is not a success rate.'
- Lists (only shown if at least 3 qualifying items, otherwise 'Not enough data yet'):
  1. Most documented business types (by case_count)
  2. Lowest reported capital among cases with status = running (median + range)
  3. Fastest reported time to break-even (median)
  4. Highest shutdown share, with failure reasons that appear in 2+ cases
  5. Emerging business types
- AI Note: optional, free tier. Prompt receives ONLY computed stats.
  Code verification extracts every number from the AI note and confirms each one exists in the input stats.
  If any number is missing/different, discard note.
- Trends: month-over-month change when >= 2 previous monthly reports exist.
"""

import os
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Dict, Any, List, Optional, Tuple

from pipeline.currency_utils import format_inr
from build_site import load_config, render_html_page

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FIXTURES_DIR = BASE_DIR / "fixtures"
SITE_DIR = BASE_DIR / "site"
PREVIEW_DIR = BASE_DIR / "preview"
IDEAS_DATA_DIR = DATA_DIR / "ideas"


FORBIDDEN_WORDS = [
    r"\byou should\b",
    r"\bbest business\b",
    r"\bstart this\b",
    r"\btop pick\b",
    r"\brecommended business\b",
    r"\bguaranteed\b",
    r"\bgreat investment\b",
    r"\bhigh profit opportunity\b"
]


def check_forbidden_words(text: str) -> List[str]:
    violations = []
    for pattern in FORBIDDEN_WORDS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(pattern)
    return violations


def extract_numbers_from_text(text: str) -> List[float]:
    """Finds all numeric amounts or counts mentioned in text."""
    # Match numbers including decimals
    matches = re.findall(r'\b\d+(?:\.\d+)?\b', text.replace(',', ''))
    return [float(m) for m in matches]


def verify_ai_note_numbers(ai_note: str, input_numbers: List[float]) -> bool:
    """Verifies that every single number in the AI note exists in the input stats."""
    note_numbers = extract_numbers_from_text(ai_note)
    if not note_numbers:
        return True

    # Check each number in note against input numbers within float rounding tolerance
    for n in note_numbers:
        match_found = any(abs(n - inp) < 0.01 or (inp > 0 and abs(n - (inp / 100000)) < 0.01) or (inp > 0 and abs(n - (inp / 10000000)) < 0.01) for inp in input_numbers)
        if not match_found:
            return False
    return True


def compute_monthly_report_data(cases: List[Dict[str, Any]], business_types: List[Dict[str, Any]], ym: str) -> Dict[str, Any]:
    """Pure-code calculation for the monthly report."""
    type_map = {bt["slug"]: bt for bt in business_types}

    # Group cases by type
    cases_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for c in cases:
        bt_slug = c.get("business_type")
        if bt_slug:
            cases_by_type.setdefault(bt_slug, []).append(c)

    ranked_types = []
    emerging_types = []

    for bt in business_types:
        slug = bt["slug"]
        t_cases = cases_by_type.get(slug, [])
        c_count = len(t_cases)

        if c_count >= 5:
            # Metrics for ranked types
            running_capitals = [c["capital_invested_inr"] for c in t_cases if c.get("status") == "running" and c.get("capital_invested_inr") is not None]
            breakevens = [c["time_to_breakeven_months"] for c in t_cases if c.get("time_to_breakeven_months") is not None]
            shut_downs = [c for c in t_cases if c.get("status") == "shut_down"]
            shutdown_share = (len(shut_downs) / c_count) if c_count > 0 else 0.0

            # Failures in 2+ cases
            fail_counts = {}
            for c in t_cases:
                for rf in c.get("what_failed", []):
                    clean_rf = rf.strip()
                    if clean_rf:
                        fail_counts[clean_rf] = fail_counts.get(clean_rf, 0) + 1
            common_fails = [rf for rf, cnt in fail_counts.items() if cnt >= 2]

            ranked_types.append({
                "slug": slug,
                "name": bt["name"],
                "case_count": c_count,
                "running_capitals": {
                    "min": min(running_capitals) if running_capitals else None,
                    "median": median(running_capitals) if running_capitals else None,
                    "max": max(running_capitals) if running_capitals else None,
                    "count": len(running_capitals)
                },
                "breakeven_median": median(breakevens) if breakevens else None,
                "shutdown_share": round(shutdown_share, 3),
                "shutdown_count": len(shut_downs),
                "common_failure_reasons": common_fails
            })
        elif 1 <= c_count < 5:
            emerging_types.append({
                "slug": slug,
                "name": bt["name"],
                "case_count": c_count,
                "description": bt.get("description", "")
            })

    # List 1: Most documented business types (ranked by case_count desc)
    list_1 = sorted(ranked_types, key=lambda x: x["case_count"], reverse=True)

    # List 2: Lowest reported capital among running cases
    list_2_eligible = [t for t in ranked_types if t["running_capitals"]["median"] is not None]
    list_2 = sorted(list_2_eligible, key=lambda x: x["running_capitals"]["median"])

    # List 3: Fastest reported time to breakeven
    list_3_eligible = [t for t in ranked_types if t["breakeven_median"] is not None]
    list_3 = sorted(list_3_eligible, key=lambda x: x["breakeven_median"])

    # List 4: Highest shutdown share
    list_4 = sorted(ranked_types, key=lambda x: x["shutdown_share"], reverse=True)

    # List 5: Emerging business types
    list_5 = sorted(emerging_types, key=lambda x: x["case_count"], reverse=True)

    return {
        "report_month": ym,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d"),
        "ranked_types": ranked_types,
        "emerging_types": emerging_types,
        "list_1_most_documented": list_1,
        "list_2_lowest_capital": list_2,
        "list_3_fastest_breakeven": list_3,
        "list_4_highest_shutdown": list_4,
        "list_5_emerging": list_5,
    }


def generate_ai_note(list_title: str, items: List[Dict[str, Any]], model_name: str) -> Optional[str]:
    """Generates an optional AI note using Gemini free tier, strictly verifying numbers."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""Write 2-3 completely neutral, factual sentences summarizing these calculated statistics for the table '{list_title}'.
DO NOT advise, recommend, or give opinions. DO NOT say 'you should', 'best', or 'opportunity'.
DO NOT invent any numbers. Output plain sentences only.

DATA:
{json.dumps(items[:5], indent=2)}
"""
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        note = response.text.strip()

        # Check for forbidden words
        if check_forbidden_words(note):
            print("AI note discarded: contains forbidden advisory phrases.")
            return None

        # Collect all numeric values in input data
        input_nums = []
        for it in items[:5]:
            for k, v in it.items():
                if isinstance(v, (int, float)):
                    input_nums.append(float(v))
                elif isinstance(v, dict):
                    for subk, subv in v.items():
                        if isinstance(subv, (int, float)):
                            input_nums.append(float(subv))

        if not verify_ai_note_numbers(note, input_nums):
            print("AI note discarded: contains numbers not present in source input stats.")
            return None

        return note
    except Exception as e:
        print(f"Skipping AI note generation: {e}")
        return None


def get_previous_reports(ideas_dir: Path) -> List[Dict[str, Any]]:
    reports = []
    if ideas_dir.exists():
        for f in sorted(ideas_dir.glob("*.json")):
            with open(f, "r", encoding="utf-8") as rf:
                reports.append(json.load(rf))
    return reports


def render_report_html(report_data: Dict[str, Any], previous_reports: List[Dict[str, Any]], config: Dict[str, Any], is_fixture: bool = False) -> str:
    ym = report_data["report_month"]
    dt = datetime.strptime(ym, "%Y-%m")
    month_name = dt.strftime("%B %Y")

    content = [
        f"<h1>What the Research Shows this Month: {month_name}</h1>",
        "<div class=\"neutral-callout\"><strong>Methodology & Scope Notice:</strong> Based on cases reported by news and public records. Cases that were never reported are not counted, so this is not a success rate. Business types are ranked only if they have 5 or more verified cases. Categories with 1 to 4 cases are categorized as Emerging.</div>"
    ]

    # Trends if >= 2 previous monthly reports exist
    if len(previous_reports) >= 2:
        last_rep = previous_reports[-1]
        content.append("<h2>Documented Month-over-Month Changes</h2>")
        content.append("<p>Comparing verified cases and median capital against the previous monthly report:</p>")
        content.append("<div class=\"grid grid-2\">")
        # Match types
        last_type_map = {t["slug"]: t for t in last_rep.get("ranked_types", [])}
        for rt in report_data.get("ranked_types", []):
            slug = rt["slug"]
            if slug in last_type_map:
                prev_rt = last_type_map[slug]
                case_diff = rt["case_count"] - prev_rt["case_count"]
                prev_med = prev_rt["running_capitals"]["median"]
                curr_med = rt["running_capitals"]["median"]
                med_diff_str = ""
                if prev_med is not None and curr_med is not None:
                    diff_val = curr_med - prev_med
                    med_diff_str = f" | Median Capital Change: {format_inr(diff_val)}"
                content.append(f"""
                  <div class="card">
                    <span class="card-title"><a href="/types/{slug}/">{rt['name']}</a></span>
                    <p>Change vs last month: {case_diff:+d} cases{med_diff_str}</p>
                  </div>
                """)
        content.append("</div>")

    # Render 5 Lists (Show only if >= 3 qualifying items)
    lists = [
        ("1. Most Documented Business Types", "Ranked by total verified case count in public records.", report_data["list_1_most_documented"], "case_count"),
        ("2. Lowest Reported Capital (Running Cases)", "Ranked by median capital invested among operating businesses.", report_data["list_2_lowest_capital"], "capital"),
        ("3. Fastest Reported Time to Breakeven", "Ranked by shortest median months to achieve operational breakeven.", report_data["list_3_fastest_breakeven"], "breakeven"),
        ("4. Highest Documented Shutdown Share", "Proportion of verified cases that ceased operations, with documented reasons.", report_data["list_4_highest_shutdown"], "shutdown"),
    ]

    for title, desc, items, kind in lists:
        content.append(f"<h2>{title}</h2>")
        content.append(f"<p>{desc}</p>")

        if len(items) < 3:
            content.append("<div class=\"neutral-callout\">Not enough data yet (minimum 3 qualifying ranked categories required).</div>")
            continue

        content.append("<div class=\"grid grid-2\">")
        for idx, it in enumerate(items, 1):
            slug = it["slug"]
            extra_info = ""
            if kind == "case_count":
                extra_info = f"<p>Documented cases: <strong>{it['case_count']}</strong></p>"
            elif kind == "capital":
                caps = it["running_capitals"]
                extra_info = f"<p>Median Capital: <strong>{format_inr(caps['median'])}</strong><br>Range: {format_inr(caps['min'])} – {format_inr(caps['max'])} ({caps['count']} cases)</p>"
            elif kind == "breakeven":
                extra_info = f"<p>Median Breakeven: <strong>{it['breakeven_median']} months</strong></p>"
            elif kind == "shutdown":
                reasons = ", ".join(it["common_failure_reasons"]) if it["common_failure_reasons"] else "None repeated in 2+ cases"
                extra_info = f"<p>Shutdown Share: <strong>{int(it['shutdown_share'] * 100)}%</strong> ({it['shutdown_count']}/{it['case_count']} cases)<br>Recurring reasons: {reasons}</p>"

            content.append(f"""
              <div class="card">
                <div class="card-header">
                  <span class="card-title">#{idx} <a href="/types/{slug}/">{it['name']}</a></span>
                  <span class="badge badge-unknown">{it['case_count']} cases</span>
                </div>
                {extra_info}
                <div class="card-meta"><a href="/types/{slug}/">View cases for {it['name']} &rarr;</a></div>
              </div>
            """)
        content.append("</div>")

    # List 5: Emerging Business Types
    content.append("<h2>5. Emerging Business Types (Early Signal, Too Few Cases)</h2>")
    content.append("<p>Categories with 1 to 4 verified cases. These are not ranked due to insufficient sample size.</p>")
    emerging = report_data["list_5_emerging"]
    if not emerging:
        content.append("<p>No business types currently classified as emerging.</p>")
    else:
        content.append("<div class=\"grid grid-2\">")
        for em in emerging:
            slug = em["slug"]
            content.append(f"""
              <div class="card">
                <div class="card-header">
                  <span class="card-title"><a href="/types/{slug}/">{em['name']}</a></span>
                  <span class="badge badge-unknown">{em['case_count']} cases</span>
                </div>
                <p>{em['description']}</p>
                <div class="card-meta"><a href="/types/{slug}/">View individual records &rarr;</a></div>
              </div>
            """)
        content.append("</div>")

    return render_html_page(
        f"What the Research Shows this Month: {month_name}",
        f"Factual monthly research report on documented businesses in India for {month_name}. Empirical capital, breakeven, and outcomes.",
        f"/ideas/{ym}/",
        "\n".join(content),
        config,
        is_fixture=is_fixture
    )


def build_monthly_report(ym: Optional[str] = None, use_fixtures: bool = False, output_dir: Optional[Path] = None):
    config = load_config()
    current_ym = ym or datetime.utcnow().strftime("%Y-%m")

    # Determine destination directory
    dest_dir = output_dir if output_dir is not None else (PREVIEW_DIR if use_fixtures else SITE_DIR)

    # Load cases
    cases_dir = FIXTURES_DIR / "cases" if use_fixtures else DATA_DIR / "cases"
    cases = []
    if cases_dir.exists():
        for cf in sorted(cases_dir.glob("*.json")):
            with open(cf, "r", encoding="utf-8") as f:
                cdata = json.load(f)
                if not use_fixtures and cdata.get("is_fixture", False):
                    continue
                cases.append(cdata)

    # Load business types
    with open(DATA_DIR / "business_types.json", "r", encoding="utf-8") as f:
        business_types = json.load(f)

    # Compute report
    report_data = compute_monthly_report_data(cases, business_types, current_ym)

    # Save report JSON
    ideas_data_dir = FIXTURES_DIR / "ideas" if use_fixtures else IDEAS_DATA_DIR
    ideas_data_dir.mkdir(parents=True, exist_ok=True)
    with open(ideas_data_dir / f"{current_ym}.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    # Load past reports for trends
    previous_reports = [r for r in get_previous_reports(ideas_data_dir) if r.get("report_month") != current_ym]

    # Generate HTML page for this month
    month_dir = dest_dir / "ideas" / current_ym
    month_dir.mkdir(parents=True, exist_ok=True)
    report_html = render_report_html(report_data, previous_reports, config, is_fixture=use_fixtures)

    # Audit HTML for forbidden words
    violations = check_forbidden_words(report_html)
    if violations:
        raise ValueError(f"CRITICAL: Forbidden advising phrases found in report: {violations}")

    with open(month_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(report_html)

    # Build /ideas/ archive page
    all_reports = get_previous_reports(ideas_data_dir)
    archive_content = [
        "<h1>Monthly Ideas Reports Archive</h1>",
        "<p class=\"neutral-callout\">Empirical monthly reports compiling verified business outcomes, capital investments, and operational factors across India. Neutral documentation only.</p>",
        "<div class=\"grid grid-2\">"
    ]
    for rep in reversed(all_reports):
        rep_ym = rep.get("report_month", "")
        dt = datetime.strptime(rep_ym, "%Y-%m")
        name = dt.strftime("%B %Y")
        archive_content.append(f"""
          <div class="card">
            <div class="card-header">
              <a href="/ideas/{rep_ym}/" class="card-title">Report: {name}</a>
              <span class="badge badge-unknown">{len(rep.get('ranked_types', []))} ranked</span>
            </div>
            <p>Empirical breakdown of {rep_ym} documented business cases and verified figures.</p>
            <div class="card-meta"><a href="/ideas/{rep_ym}/">Read monthly report &rarr;</a></div>
          </div>
        """)
    archive_content.append("</div>")

    (dest_dir / "ideas").mkdir(parents=True, exist_ok=True)
    with open(dest_dir / "ideas" / "index.html", "w", encoding="utf-8") as f:
        f.write(render_html_page(
            "Monthly Ideas Reports Archive",
            "Archive of factual monthly research reports documenting real business outcomes across India.",
            "/ideas/",
            "\n".join(archive_content),
            config,
            is_fixture=use_fixtures
        ))

    print(f"Monthly report for {current_ym} built successfully at {month_dir}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monthly ideas report builder.")
    parser.add_argument("--month", type=str, help="Report month in YYYY-MM format")
    parser.add_argument("--use-fixtures", action="store_true", help="Use test fixtures instead of production data")
    args = parser.parse_args()
    build_monthly_report(ym=args.month, use_fixtures=args.use_fixtures)
