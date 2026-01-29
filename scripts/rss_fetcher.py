"""
RSS Fetcher and Parser Module
Responsible for downloading RSS XML and extracting content for the target date.
"""
import feedparser
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
import re
from config import RSS_URL, RSS_TIMEOUT

class NewsLoader:
    """Handles fetching and parsing of news from RSS feeds"""
    
    def __init__(self, source_url: str = None):
        """
        Initialize the news loader
        Args:
            source_url: URL of the RSS feed. Defaults to RSS_URL from config.
        """
        self.url = source_url or RSS_URL
        self.request_timeout = RSS_TIMEOUT
        self.cache = None

    def pull_feed(self) -> feedparser.FeedParserDict:
        """Retrieve and parse the remote RSS feed"""
        print(f"📥 Pulling RSS data: {self.url}")
        try:
            resp = requests.get(
                self.url,
                timeout=self.request_timeout,
                headers={"User-Agent": "TomatoNews/2.0 (compatible; NewsBot/1.0)"}
            )
            resp.raise_for_status()
            parsed_data = feedparser.parse(resp.content)
            
            if parsed_data.bozo:
                print(f"⚠️ Feed parsing issue: {parsed_data.bozo_exception}")
                
            print(f"✅ Feed loaded: {len(parsed_data.entries)} items found")
            self.cache = parsed_data
            return parsed_data
        except requests.RequestException as err:
            raise RuntimeError(f"Failed to download feed: {err}")
        except Exception as err:
            raise RuntimeError(f"Failed to process feed: {err}")

    def fetch_by_day(self, date_str: str, feed_data: feedparser.FeedParserDict = None) -> Optional[Dict[str, Any]]:
        """
        Locate news entry matching a specific calendar day
        Args:
            date_str: Target date in YYYY-MM-DD format
            feed_data: Existing feed data. If None, it will be pulled.
        Returns:
            Processed entry or None if missing.
        """
        if feed_data is None:
            feed_data = self.pull_feed()
            
        try:
            target_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError(f"Date format mismatch: {date_str} (use YYYY-MM-DD)")

        print(f"🔍 Locating content for: {date_str}")
        for item in feed_data.entries:
            # Check published timestamp
            if hasattr(item, 'published_parsed') and item.published_parsed:
                pub_time = datetime(*item.published_parsed[:6], tzinfo=timezone.utc)
                if self._compare_dates(pub_time, target_obj):
                    return self._format_item(item)
            
            # Check URL pattern for date
            if hasattr(item, 'link'):
                extracted = self._parse_url_date(item.link)
                if extracted == date_str:
                    return self._format_item(item)

        print(f"❌ No matching content for {date_str}")
        return None

    def _compare_dates(self, d1: datetime, d2: datetime) -> bool:
        """Verify if two timestamps fall on the same calendar day"""
        return d1.date() == d2.date()

    def _parse_url_date(self, url: str) -> Optional[str]:
        """Extract YYYY-MM-DD from URL path segments"""
        patterns = [
            r'/issues/(\d{2})-(\d{2})-(\d{2})-',            
            r'/issues/(\d{4})-(\d{2})-(\d{2})-',              
        ]
        for p in patterns:
            found = re.search(p, url)
            if found:
                y, m, d = found.groups()
                full_y = f"20{y}" if len(y) == 2 else y
                return f"{full_y}-{m}-{d}"
        return None

    def _format_item(self, raw_item) -> Dict[str, Any]:
        """Clean and structure raw RSS entry data"""
        out = {
            "title": raw_item.get("title", ""),
            "link": raw_item.get("link", ""),
            "guid": raw_item.get("id", raw_item.get("guid", raw_item.get("link", ""))),
            "description": raw_item.get("description", ""),
            "content": "",
            "pubDate": raw_item.get("published", raw_item.get("updated", ""))
        }
        
        # Priority for full content
        if hasattr(raw_item, 'content') and raw_item.content:
            out["content"] = raw_item.content[0].get('value', '')
        elif hasattr(raw_item, 'summary'):
            out["content"] = raw_item.summary
        else:
            out["content"] = out["description"]
            
        # Unescape HTML entities
        out["content"] = out["content"].replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return out

    def get_latest_timestamp(self, feed_data: feedparser.FeedParserDict = None) -> Optional[str]:
        """Identify the date of the most recent item in the feed"""
        if feed_data is None:
            feed_data = self.pull_feed()
        if not feed_data.entries:
            return None
            
        top_item = feed_data.entries[0]
        if hasattr(top_item, 'link'):
            url_date = self._parse_url_date(top_item.link)
            if url_date:
                return url_date
        if hasattr(top_item, 'published_parsed') and top_item.published_parsed:
            ts = datetime(*top_item.published_parsed[:6], tzinfo=timezone.utc)
            return ts.strftime("%Y-%m-%d")
        return None

    def get_available_range(self, feed_data: feedparser.FeedParserDict = None) -> tuple:
        """Determine the start and end dates present in the feed"""
        if feed_data is None:
            feed_data = self.pull_feed()
        if not feed_data.entries:
            return None, None
            
        found_dates = []
        for item in feed_data.entries:
            if hasattr(item, 'link'):
                d = self._parse_url_date(item.link)
                if d:
                    found_dates.append(d)
        
        if not found_dates:
            return None, None
        return min(found_dates), max(found_dates)

def fetch_rss_content(target_date: str) -> Optional[Dict[str, Any]]:
    """Legacy helper for backward compatibility"""
    loader = NewsLoader()
    data = loader.pull_feed()
    return loader.fetch_by_day(target_date, data)
