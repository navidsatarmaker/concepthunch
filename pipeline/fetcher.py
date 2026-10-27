"""
Article fetcher module.
Fetches articles from RSS/listing feeds in sources.json:
- Respects robots.txt
- Sends a descriptive User-Agent
- Skips already processed URLs
- Rate limits requests
- Strips HTML to clean text
"""

import time
import urllib.robotparser
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None


def can_fetch_url(url: str, user_agent: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        # If robots.txt cannot be fetched, default to permissive but cautious
        return True


def clean_html_text(html: str) -> str:
    """Removes scripts, styles, and HTML tags, returning plain text."""
    # Remove script and style elements
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_feed_articles(source: Dict[str, Any], user_agent: str, processed_urls: set, max_articles: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches latest article links and titles from an RSS/Atom feed.
    """
    if not requests:
        return []

    feed_url = source.get("listing_url")
    if not feed_url or not feed_url.endswith((".xml", ".rss", "/feed", "/feed/")):
        return []

    headers = {"User-Agent": user_agent}
    try:
        resp = requests.get(feed_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
    except Exception:
        return []

    articles = []
    # Try RSS channel items
    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else root.findall("item")
    if not items:
        # Try Atom entry items
        items = root.findall("{http://www.w3.org/2005/Atom}entry")

    for item in items:
        link_elem = item.find("link")
        link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
        if not link and link_elem is not None and "href" in link_elem.attrib:
            link = link_elem.attrib["href"]

        if not link or link in processed_urls:
            continue

        title_elem = item.find("title")
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

        articles.append({
            "source_id": source.get("id"),
            "source_name": source.get("name"),
            "source_type": source.get("source_tier"),
            "url": link,
            "title": title
        })

        if len(articles) >= max_articles:
            break

    return articles


def fetch_article_content(url: str, user_agent: str, delay_seconds: float = 1.0) -> Optional[str]:
    """
    Fetches article HTML and returns cleaned text if allowed and non-paywalled.
    """
    if not requests:
        return None

    if not can_fetch_url(url, user_agent):
        print(f"Skipping {url}: Disallowed by robots.txt")
        return None

    time.sleep(delay_seconds)
    headers = {"User-Agent": user_agent}

    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 429:
            print("Received HTTP 429 Rate Limit from server.")
            return "RATE_LIMIT_HIT"
        if resp.status_code != 200:
            return None

        # Check for paywall indicators
        content_lower = resp.text.lower()
        paywall_phrases = ["subscribe to read", "paywall", "exclusive for subscribers", "already a subscriber?"]
        if any(p in content_lower for p in paywall_phrases):
            print(f"Skipping {url}: Paywall detected.")
            return None

        return clean_html_text(resp.text)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
