"""
Static Site Builder for Indian Business Cases.
Pure Python 3.11, zero framework dependencies.
Reads JSON data, computes summaries (pure code), and writes static HTML to site/.
Enforces:
- Neutral language
- Verbatim quote display
- "Not found" for missing fields
- Strict isolation of fixtures (never in prod unless --use-fixtures)
- Code-only summaries with < 3 cases threshold
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Dict, List, Any, Optional

from pipeline.currency_utils import format_inr

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FIXTURES_DIR = BASE_DIR / "fixtures"
SITE_DIR = BASE_DIR / "site"
CONFIG_PATH = BASE_DIR / "config.json"


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_field_stats(values: List[float | int]) -> Optional[Dict[str, Any]]:
    if not values:
        return None
    return {
        "min": min(values),
        "median": median(values),
        "max": max(values),
        "count": len(values),
    }


def compute_summary_for_type(slug: str, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure code summary computation. No LLM."""
    type_cases = [c for c in cases if c.get("business_type") == slug]
    count = len(type_cases)

    # Collect numbers
    capitals = [c["capital_invested_inr"] for c in type_cases if c.get("capital_invested_inr") is not None]
    monthly_costs = [c["monthly_cost_inr"] for c in type_cases if c.get("monthly_cost_inr") is not None]
    revenues = [c["revenue_inr"] for c in type_cases if c.get("revenue_inr") is not None]
    breakevens = [c["time_to_breakeven_months"] for c in type_cases if c.get("time_to_breakeven_months") is not None]

    # Outcomes count
    outcomes = {"running": 0, "shut_down": 0, "acquired": 0, "unknown": 0}
    for c in type_cases:
        st = c.get("status", "unknown")
        outcomes[st] = outcomes.get(st, 0) + 1

    # Common failure reasons appearing in 2+ cases
    failure_counts = {}
    for c in type_cases:
        for reason in c.get("what_failed", []):
            reason_clean = reason.strip()
            if reason_clean:
                failure_counts[reason_clean] = failure_counts.get(reason_clean, 0) + 1

    common_failures = [reason for reason, cnt in failure_counts.items() if cnt >= 2]

    return {
        "business_type": slug,
        "case_count": count,
        "has_sufficient_data": count >= 3,
        "outcomes": outcomes,
        "capital_invested_inr": compute_field_stats(capitals),
        "monthly_cost_inr": compute_field_stats(monthly_costs),
        "revenue_inr": compute_field_stats(revenues),
        "time_to_breakeven_months": compute_field_stats(breakevens),
        "common_failure_reasons": common_failures,
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
    }


def render_html_page(title: str, description: str, canonical_path: str, content: str, config: Dict[str, Any], is_fixture: bool = False) -> str:
    ads_enabled = config.get("ads", {}).get("enabled", False)
    banner_ad_html = ""
    if ads_enabled:
        banner_ad_html = '<div class="ad-slot-banner">Advertisement Slot</div>'

    fixture_banner = ""
    if is_fixture:
        fixture_banner = '<div class="fixture-alert">DEMONSTRATION RUN: DISPLAYING TEST FIXTURES (SAMPLE – NOT REAL)</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Indian Business Cases</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="https://example.com{canonical_path}">
  <link rel="stylesheet" href="/css/style.css">
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#1f2421">
</head>
<body>
  {fixture_banner}
  {banner_ad_html}
  <header>
    <div class="container header-inner">
      <a href="/" class="site-title">Indian Business Cases</a>
      <nav class="site-nav">
        <a href="/">Home</a>
        <a href="/ideas/">Monthly Reports</a>
        <a href="/methodology/">Methodology</a>
        <a href="/about/">About</a>
        <a href="/disclaimer/">Disclaimer</a>
      </nav>
    </div>
  </header>

  <main class="container">
    {content}
  </main>

  <footer>
    <div class="container">
      <div class="footer-disclaimer">
        <strong>Information Notice:</strong> This website provides factual records of reported business outcomes in India. It does not provide business, financial, or investment advice. Outlier or unrecorded outcomes are not represented.
      </div>
      <div>&copy; {datetime.utcnow().year} Indian Business Cases. Public records & news citations.</div>
      <div class="footer-nav">
        <a href="/methodology/">Methodology & Verification</a>
        <a href="/about/">About the Project</a>
        <a href="/privacy/">Privacy Policy</a>
        <a href="/disclaimer/">Full Disclaimer</a>
      </div>
    </div>
  </footer>
  <script src="/js/app.js" async></script>
</body>
</html>
"""


def build_site(use_fixtures: bool = False):
    config = load_config()

    # Clean existing generated pages in site/ before regenerating
    for sub in ["cases", "types", "ideas"]:
        target_dir = SITE_DIR / sub
        if target_dir.exists():
            shutil.rmtree(target_dir)

    # Load business types
    types_path = DATA_DIR / "business_types.json"
    business_types = []
    if types_path.exists():
        with open(types_path, "r", encoding="utf-8") as f:
            business_types = json.load(f)

    # Load cases
    cases: List[Dict[str, Any]] = []
    cases_dir = FIXTURES_DIR / "cases" if use_fixtures else DATA_DIR / "cases"

    if cases_dir.exists():
        for case_file in sorted(cases_dir.glob("*.json")):
            with open(case_file, "r", encoding="utf-8") as f:
                case_data = json.load(f)
                if not use_fixtures and case_data.get("is_fixture", False):
                    # Hard protection: skip fixture file if accidentally located in data
                    continue
                cases.append(case_data)

    print(f"Building site. Mode: {'FIXTURE' if use_fixtures else 'PRODUCTION'}. Loaded {len(cases)} cases.")

    # Recompute and persist summaries
    summaries_dir = FIXTURES_DIR / "summaries" if use_fixtures else DATA_DIR / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)

    type_summaries = {}
    for bt in business_types:
        slug = bt["slug"]
        summ = compute_summary_for_type(slug, cases)
        type_summaries[slug] = summ
        with open(summaries_dir / f"{slug}.json", "w", encoding="utf-8") as f:
            json.dump(summ, f, indent=2)

    # Build sitemap list
    sitemap_urls = ["/", "/ideas/", "/methodology/", "/about/", "/privacy/", "/disclaimer/"]

    # 1. Homepage
    home_content = []
    home_content.append("""
      <h1>Real Business Outcomes in India</h1>
      <p class="neutral-callout">
        A public archive of researched, factual operational outcomes in Indian commerce: reported capital investment, monthly operating costs, recorded revenues, and documented reasons for success or closure.
      </p>
    """)

    home_content.append("<h2>Browse by Business Type</h2><div class=\"grid grid-2\">")
    for bt in business_types:
        slug = bt["slug"]
        summ = type_summaries.get(slug, {})
        c_count = summ.get("case_count", 0)
        home_content.append(f"""
          <div class="card">
            <div class="card-header">
              <a href="/types/{slug}/" class="card-title">{bt['name']}</a>
              <span class="badge badge-unknown">{c_count} cases</span>
            </div>
            <p>{bt['description']}</p>
            <div class="card-meta">Category: {bt['category']}</div>
          </div>
        """)
        sitemap_urls.append(f"/types/{slug}/")
    home_content.append("</div>")

    home_content.append("<h2>Recently Documented Cases</h2>")
    if not cases:
        home_content.append("<p>No verified cases currently in the database.</p>")
    else:
        home_content.append("<div class=\"grid grid-2\">")
        for c in cases[:10]:
            cid = c["id"]
            sitemap_urls.append(f"/cases/{cid}/")
            status = c.get("status", "unknown")
            cap_str = format_inr(c.get("capital_invested_inr"))
            cost_str = format_inr(c.get("monthly_cost_inr"))
            rev_str = format_inr(c.get("revenue_inr"))
            rev_period = f" ({c.get('revenue_period')})" if c.get("revenue_period") else ""
            home_content.append(f"""
              <div class="card">
                <div class="card-header">
                  <a href="/cases/{cid}/" class="card-title">{c.get('business_name')}</a>
                  <span class="badge badge-{status}">{status.replace('_', ' ')}</span>
                </div>
                <p>Location: {c.get('city')}, {c.get('state')} (Started {c.get('year_started', 'Not found')})</p>
                <div class="metrics-list">
                  <div class="metric-item">
                    <span class="metric-label">Capital Invested</span>
                    <span class="metric-value {'' if c.get('capital_invested_inr') is not None else 'metric-not-found'}">{cap_str}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">Monthly Cost</span>
                    <span class="metric-value {'' if c.get('monthly_cost_inr') is not None else 'metric-not-found'}">{cost_str}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">Reported Revenue</span>
                    <span class="metric-value {'' if c.get('revenue_inr') is not None else 'metric-not-found'}">{rev_str}{rev_period}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">Breakeven</span>
                    <span class="metric-value {'' if c.get('time_to_breakeven_months') is not None else 'metric-not-found'}">{str(c.get('time_to_breakeven_months')) + ' mos' if c.get('time_to_breakeven_months') is not None else 'Not found'}</span>
                  </div>
                </div>
                <div class="card-meta">
                  Source: {c.get('source_name')} ({c.get('source_type')}) · {c.get('published_date', 'Date not found')}
                </div>
              </div>
            """)
        home_content.append("</div>")

    (SITE_DIR).mkdir(parents=True, exist_ok=True)
    with open(SITE_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(render_html_page(
            "Documented Outcomes of Businesses in India",
            "Researched factual numbers on capital, operating costs, revenues, and outcomes of real businesses across India.",
            "/",
            "\n".join(home_content),
            config,
            is_fixture=use_fixtures
        ))

    # 2. Business Type Pages
    for bt in business_types:
        slug = bt["slug"]
        summ = type_summaries.get(slug, {})
        type_cases = [c for c in cases if c.get("business_type") == slug]
        type_dir = SITE_DIR / "types" / slug
        type_dir.mkdir(parents=True, exist_ok=True)

        t_content = [f"<h1>{bt['name']}</h1>", f"<p>{bt['description']}</p>"]

        if not summ.get("has_sufficient_data"):
            t_content.append("""
              <div class="neutral-callout">
                <strong>Data note:</strong> Fewer than 3 verified cases are documented for this business type. Summary statistics and ranges are only computed when at least 3 cases exist. Documented individual cases are listed below.
              </div>
            """)
        else:
            cap_stat = summ.get("capital_invested_inr")
            t_content.append("<h2>Computed Metrics (>= 3 Cases)</h2>")
            t_content.append("<div class=\"metrics-list\">")
            if cap_stat:
                t_content.append(f"""
                  <div class="metric-item">
                    <span class="metric-label">Capital Range (Min - Max)</span>
                    <span class="metric-value">{format_inr(cap_stat['min'])} – {format_inr(cap_stat['max'])}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">Median Capital Invested</span>
                    <span class="metric-value">{format_inr(int(cap_stat['median']))}</span>
                  </div>
                """)
            t_content.append("</div>")

            # Failure reasons if 2+
            common_fails = summ.get("common_failure_reasons", [])
            if common_fails:
                t_content.append("<h3>Documented Recurring Difficulties (Reported in 2+ cases)</h3><ul class=\"factor-list\">")
                for cf in common_fails:
                    t_content.append(f"<li>{cf}</li>")
                t_content.append("</ul>")

        t_content.append(f"<h2>Documented Cases ({len(type_cases)})</h2>")
        if not type_cases:
            t_content.append("<p>No cases documented yet for this business category.</p>")
        else:
            t_content.append("<div class=\"grid grid-2\">")
            for c in type_cases:
                cid = c["id"]
                status = c.get("status", "unknown")
                t_content.append(f"""
                  <div class="card">
                    <div class="card-header">
                      <a href="/cases/{cid}/" class="card-title">{c.get('business_name')}</a>
                      <span class="badge badge-{status}">{status.replace('_', ' ')}</span>
                    </div>
                    <p>{c.get('city')}, {c.get('state')} · Started {c.get('year_started', 'Not found')}</p>
                    <div class="card-meta">
                      <a href="/cases/{cid}/">View full case records & verified quotes &rarr;</a>
                    </div>
                  </div>
                """)
            t_content.append("</div>")

        with open(type_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(render_html_page(
                f"{bt['name']} Cases & Data in India",
                f"Reported financial data, outcomes, and records for {bt['name']} in India.",
                f"/types/{slug}/",
                "\n".join(t_content),
                config,
                is_fixture=use_fixtures
            ))

    # 3. Individual Case Pages
    for c in cases:
        cid = c["id"]
        case_dir = SITE_DIR / "cases" / cid
        case_dir.mkdir(parents=True, exist_ok=True)
        status = c.get("status", "unknown")

        c_content = [
            f"<div class=\"card-header\"><h1>{c.get('business_name')}</h1><span class=\"badge badge-{status}\">{status.replace('_', ' ')}</span></div>",
            f"<p><strong>Location:</strong> {c.get('city')}, {c.get('state')} | <strong>Year Started:</strong> {c.get('year_started', 'Not found')}</p>",
            f"<p class=\"neutral-callout\"><strong>Summary:</strong> {c.get('own_summary')}</p>",
            "<h2>Documented Financials & Verified Quotes</h2>",
            "<div class=\"grid grid-2\">"
        ]

        fields = [
            ("Capital Invested", c.get("capital_invested_inr"), c.get("capital_invested_inr_quote")),
            ("Monthly Cost", c.get("monthly_cost_inr"), c.get("monthly_cost_inr_quote")),
            (f"Revenue ({c.get('revenue_period', 'period not stated')})", c.get("revenue_inr"), c.get("revenue_inr_quote")),
            ("Profit or Loss", c.get("profit_or_loss_inr"), c.get("profit_or_loss_inr_quote")),
            ("Time to Breakeven", f"{c.get('time_to_breakeven_months')} months" if c.get("time_to_breakeven_months") is not None else None, c.get("time_to_breakeven_months_quote"))
        ]

        for label, val, quote in fields:
            display_val = format_inr(val) if isinstance(val, int) else (val if val is not None else "Not found")
            quote_html = f"<div class=\"verified-quote\">\"{quote}\"</div>" if quote else "<div class=\"verified-quote\">No supporting quote recorded</div>"
            c_content.append(f"""
              <div class="card">
                <span class="metric-label">{label}</span>
                <span class="metric-value {'' if val is not None else 'metric-not-found'}">{display_val}</span>
                {quote_html}
              </div>
            """)
        c_content.append("</div>")

        # Factors reported
        what_worked = c.get("what_worked", [])
        what_failed = c.get("what_failed", [])

        c_content.append("<h2>Reported Operational Observations</h2>")
        c_content.append("<div class=\"grid grid-2\">")
        c_content.append("<div class=\"card\"><h3>Reported Effective Factors</h3>")
        if what_worked:
            c_content.append("<ul class=\"factor-list\">" + "".join(f"<li>{item}</li>" for item in what_worked) + "</ul>")
        else:
            c_content.append("<p class=\"metric-not-found\">None specifically cited in source text.</p>")
        c_content.append("</div>")

        c_content.append("<div class=\"card\"><h3>Reported Difficulties / Failure Factors</h3>")
        if what_failed:
            c_content.append("<ul class=\"factor-list\">" + "".join(f"<li>{item}</li>" for item in what_failed) + "</ul>")
        else:
            c_content.append("<p class=\"metric-not-found\">None specifically cited in source text.</p>")
        c_content.append("</div></div>")

        # Source Verification
        c_content.append(f"""
          <h2>Source & Verification Audit</h2>
          <div class="card">
            <p><strong>Source Name:</strong> {c.get('source_name')} ({c.get('source_type')})</p>
            <p><strong>Published Date:</strong> {c.get('published_date', 'Not found')}</p>
            <p><strong>Original Article Reference:</strong> <a href="{c.get('source_url')}" target="_blank" rel="noopener noreferrer">View Original Source Article</a></p>
            <p><strong>Code Verification Check:</strong> Quotes verified: {'Yes' if c.get('verification', {}).get('quotes_verified') else 'No'} | Cross-checked: {'Yes' if c.get('verification', {}).get('cross_checked') else 'No'}</p>
          </div>
        """)

        with open(case_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(render_html_page(
                f"{c.get('business_name')} – Business Case Record",
                f"Factual case report for {c.get('business_name')} in {c.get('city')}, {c.get('state')}. Reported financials and operational outcomes.",
                f"/cases/{cid}/",
                "\n".join(c_content),
                config,
                is_fixture=use_fixtures
            ))

    # 4. Methodology Page
    meth_dir = SITE_DIR / "methodology"
    meth_dir.mkdir(parents=True, exist_ok=True)
    with open(meth_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(render_html_page(
            "Methodology & Verification",
            "Our data collection methodology, quote verification rules, source whitelist, and statistical criteria.",
            "/methodology/",
            """
            <h1>Methodology & Research Standards</h1>
            <div class="neutral-callout">
              This platform documents empirical, public records of business ventures in India. We do not provide advice, recommendations, or speculative projections.
            </div>
            <h2>1. Whitelisted Trusted Sources</h2>
            <p>We only process public reporting from recognized business publications, government filings (e.g. KVIC/PMEGP, MSME-DI), and academic incubation case studies (IITs, IIMs). We strictly respect robots.txt and exclude paywalled or login-gated content.</p>
            <h2>2. The "Not Found" Standard</h2>
            <p>If a metric (such as revenue, capital, or operating cost) is not stated explicitly in the original source, it is marked as <strong>Not found</strong>. We never estimate, interpolate, or extrapolate figures.</p>
            <h2>3. Pure-Code Verbatim Quote Verification</h2>
            <p>Every number presented must match an exact, verbatim quotation of under 25 words from the original source text. A pure-code verification algorithm confirms that the extracted number appears inside that exact sentence before the record is approved.</p>
            <h2>4. Equal Visual Weight for Failures</h2>
            <p>Business closures and operational struggles are given identical prominence and typography as profitable businesses. Understanding operational pitfalls is critical to factual documentation.</p>
            <h2>5. Minimum Case Thresholds for Aggregates</h2>
            <p>Aggregate ranges (minimum, median, maximum) are only displayed when a category has at least 3 documented cases. If fewer than 3 cases exist, the individual cases are shown without aggregate statistics.</p>
            """,
            config,
            is_fixture=use_fixtures
        ))

    # 5. About Page
    about_dir = SITE_DIR / "about"
    about_dir.mkdir(parents=True, exist_ok=True)
    with open(about_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(render_html_page(
            "About the Project",
            "Background, mission, and principles of the Indian Business Cases factual archive.",
            "/about/",
            """
            <h1>About Indian Business Cases</h1>
            <p>Indian Business Cases is a free, neutral repository documenting actual financial and operational data reported by Indian businesses.</p>
            <p>Unlike entrepreneurial blogs that encourage business setup without context, this platform collects empirical facts: what founders actually spent, what monthly overheads looked like, what revenues were recorded, and why ventures succeeded or ceased operations.</p>
            <h2>Operating Principles</h2>
            <ul class="factor-list">
              <li><strong>Zero advisory tone:</strong> We report "what happened", never "what you should do".</li>
              <li><strong>Zero user tracking or monetization barriers:</strong> Completely free, static, lightweight, mobile-first pages.</li>
              <li><strong>Strict factual provenance:</strong> Every data point is tied to a verified public source.</li>
            </ul>
            """,
            config,
            is_fixture=use_fixtures
        ))

    # 6. Privacy Policy Page
    privacy_dir = SITE_DIR / "privacy"
    privacy_dir.mkdir(parents=True, exist_ok=True)
    with open(privacy_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(render_html_page(
            "Privacy Policy",
            "Privacy policy for Indian Business Cases.",
            "/privacy/",
            """
            <h1>Privacy Policy</h1>
            <p>Indian Business Cases does not require user accounts, user logins, cookies, or personal information submission.</p>
            <p>No user data is sold, tracked across websites, or profiled. Server request logs, if any, are maintained solely by the hosting infrastructure (Netlify/GitHub) for standard delivery and security purposes.</p>
            """,
            config,
            is_fixture=use_fixtures
        ))

    # 7. Disclaimer Page
    disc_dir = SITE_DIR / "disclaimer"
    disc_dir.mkdir(parents=True, exist_ok=True)
    with open(disc_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(render_html_page(
            "Full Disclaimer",
            "Legal and informational disclaimer.",
            "/disclaimer/",
            """
            <h1>Information & Non-Advisory Disclaimer</h1>
            <div class="neutral-callout">
              <strong>Notice:</strong> The contents of this website are strictly for informational and educational documentation purposes.
            </div>
            <p>1. <strong>No Business or Financial Advice:</strong> Nothing on this website constitutes investment, business, legal, tax, or financial advice. We do not recommend starting, closing, purchasing, or financing any enterprise.</p>
            <p>2. <strong>Reporting Bias & Outliers:</strong> The cases featured reflect businesses reported in news publications and public records. Businesses that were never covered by media or government case studies are not included. Consequently, figures do not represent statistical averages or survival rates of all businesses in India.</p>
            <p>3. <strong>Historical Accuracy:</strong> Financial figures and quotations reflect the source reporting at the time of publication. Economic conditions, inflation, and regulations change over time.</p>
            """,
            config,
            is_fixture=use_fixtures
        ))

    # 8. Sitemap.xml
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for url in sorted(set(sitemap_urls)):
        sitemap_lines.append(f"  <url><loc>https://example.com{url}</loc><changefreq>weekly</changefreq></url>")
    sitemap_lines.append('</urlset>')

    with open(SITE_DIR / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(sitemap_lines))

    print(f"Site build complete. Output written to {SITE_DIR}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Static site generator for Indian Business Cases.")
    parser.add_argument("--use-fixtures", action="store_true", help="Build site using SAMPLE fixtures instead of production data")
    args = parser.parse_args()
    build_site(use_fixtures=args.use_fixtures)
