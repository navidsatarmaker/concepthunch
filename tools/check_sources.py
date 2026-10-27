"""
Tool to verify robots.txt compliance and feed accessibility for all sources in sources.json.

For each source:
1. Uses the exact same User-Agent configured in config.json.
2. Fetches the site's robots.txt.
3. Checks if our User-Agent is allowed to fetch the feed/listing URL.
4. If allowed and accessible, fetches the feed (without fetching any article bodies)
   to extract a sample article URL.
5. Checks if our User-Agent is allowed to fetch that sample article URL per robots.txt.
6. Rate-limits requests and strictly respects robots.txt.
7. Prints a clean, formatted table of results:
   Source Name | Feed Allowed | Article Allowed | Notes
"""

import os
import sys
import json
import time
import urllib.robotparser
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

try:
    import requests
except ImportError:
    requests = None

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
SOURCES_PATH = BASE_DIR / "sources.json"


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sources() -> List[Dict[str, Any]]:
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_robots_parser(base_url: str, user_agent: str, delay: float = 1.0) -> Tuple[Optional[urllib.robotparser.RobotFileParser], str]:
    """
    Fetches robots.txt using the specified User-Agent and returns a RobotFileParser.
    """
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()

    headers = {"User-Agent": user_agent}

    time.sleep(delay)
    try:
        if requests:
            resp = requests.get(robots_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
                return rp, "robots.txt parsed (HTTP 200)"
            elif resp.status_code == 404:
                # 404 implies no robots.txt restrictions
                rp.parse([])
                return rp, "robots.txt not found (HTTP 404 - unrestricted)"
            elif resp.status_code == 403:
                return None, f"robots.txt forbidden (HTTP 403)"
            elif resp.status_code == 429:
                return None, "robots.txt rate limited (HTTP 429)"
            else:
                return None, f"robots.txt returned HTTP {resp.status_code}"
        else:
            rp.set_url(robots_url)
            rp.read()
            return rp, "robots.txt parsed via urllib"
    except Exception as e:
        return None, f"robots.txt error: {str(e)[:35]}"


def extract_sample_article_url(feed_url: str, user_agent: str, delay: float = 1.0) -> Tuple[Optional[str], str]:
    """
    Fetches the feed XML/listing page and extracts the URL of the first article item.
    Does NOT fetch the article body itself.
    """
    if not requests:
        return None, "requests library missing"

    time.sleep(delay)
    headers = {"User-Agent": user_agent}

    try:
        resp = requests.get(feed_url, headers=headers, timeout=12)
        if resp.status_code == 429:
            return None, "Feed rate limited (HTTP 429)"
        if resp.status_code != 200:
            return None, f"Feed returned HTTP {resp.status_code}"

        # Attempt XML parsing for RSS/Atom
        try:
            root = ET.fromstring(resp.content)
            # RSS channel items
            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else root.findall("item")
            if not items:
                # Atom entry items
                items = root.findall("{http://www.w3.org/2005/Atom}entry")

            for item in items:
                link_elem = item.find("link")
                link = ""
                if link_elem is not None:
                    if link_elem.text and link_elem.text.strip():
                        link = link_elem.text.strip()
                    elif "href" in link_elem.attrib:
                        link = link_elem.attrib["href"]

                if link and link.startswith("http"):
                    return link, "Found item in feed"
        except ET.ParseError:
            # HTML listing page (e.g. government/incubator listing page)
            # Find first reasonable hyperlink in listing
            import re
            links = re.findall(r'href=[\'"](https?://[^\'">]+)[\'"]', resp.text, re.IGNORECASE)
            parsed_feed = urlparse(feed_url)
            for l in links:
                parsed_l = urlparse(l)
                if parsed_l.netloc == parsed_feed.netloc and l != feed_url and not l.endswith(('.css', '.js', '.png', '.jpg')):
                    return l, "Found link in listing"

        return None, "No article link found in feed"
    except Exception as e:
        return None, f"Feed fetch error: {str(e)[:35]}"


def check_source(source: Dict[str, Any], user_agent: str, delay: float = 1.0) -> Dict[str, Any]:
    name = source.get("name", "Unknown")
    feed_url = source.get("listing_url", "")
    notes = []

    # 1. Fetch robots.txt
    rp, robots_note = get_robots_parser(feed_url, user_agent, delay=delay)
    notes.append(robots_note)

    feed_allowed = "Unknown"
    article_allowed = "N/A"
    sample_article_url = None

    if rp is not None:
        can_feed = rp.can_fetch(user_agent, feed_url)
        feed_allowed = "Yes" if can_feed else "No"
    else:
        # Default policy if robots.txt unreachable
        feed_allowed = "Error (robots)"

    # 2. If feed is allowed, fetch feed to extract 1 sample article URL
    if feed_allowed == "Yes":
        sample_url, feed_note = extract_sample_article_url(feed_url, user_agent, delay=delay)
        if sample_url:
            sample_article_url = sample_url
            if rp is not None:
                # Check sample article URL against same domain's robots.txt
                # If sample article belongs to a different domain, fetch that domain's robots.txt
                feed_domain = urlparse(feed_url).netloc
                art_domain = urlparse(sample_url).netloc
                if art_domain == feed_domain:
                    can_art = rp.can_fetch(user_agent, sample_url)
                    article_allowed = "Yes" if can_art else "No"
                else:
                    art_rp, art_rb_note = get_robots_parser(sample_url, user_agent, delay=delay)
                    if art_rp:
                        can_art = art_rp.can_fetch(user_agent, sample_url)
                        article_allowed = "Yes" if can_art else "No"
                    else:
                        article_allowed = "Error (robots)"
            else:
                article_allowed = "Unknown"
        else:
            notes.append(feed_note)
            article_allowed = "No link"
    elif feed_allowed == "No":
        notes.append("Feed disallowed by robots.txt")

    return {
        "name": name,
        "feed_url": feed_url,
        "feed_allowed": feed_allowed,
        "article_allowed": article_allowed,
        "sample_url": sample_article_url,
        "notes": "; ".join(notes)
    }


def main():
    config = load_config()
    sources = load_sources()
    user_agent = config.get("site", {}).get("user_agent", "IndiaBusinessCasesBot/1.0 (+https://example.com/methodology)")

    print(f"Configured User-Agent: {user_agent}")
    print(f"Checking {len(sources)} sources from sources.json...")
    print("=" * 110)

    results = []
    # Polite rate limit delay between calls (1.0 sec)
    for idx, src in enumerate(sources, 1):
        print(f"[{idx}/{len(sources)}] Checking {src.get('name')}...", flush=True)
        res = check_source(src, user_agent, delay=1.0)
        results.append(res)

    print("\n" + "=" * 110)
    # Print formatted markdown / ASCII table
    header_fmt = "{:<32} | {:<14} | {:<16} | {:<50}"
    row_sep = "-" * 32 + "-+-" + "-" * 14 + "-+-" + "-" * 16 + "-+-" + "-" * 50

    print(header_fmt.format("Source Name", "Feed Allowed", "Article Allowed", "Notes"))
    print(row_sep)
    for r in results:
        notes = r["notes"]
        print(header_fmt.format(
            r["name"][:32],
            r["feed_allowed"][:14],
            r["article_allowed"][:16],
            notes
        ))
    print(row_sep)


if __name__ == "__main__":
    main()
