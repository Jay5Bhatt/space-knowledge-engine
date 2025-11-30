# tools/arxiv_fetcher.py
"""
arxiv_fetcher.py

Small wrapper for fetching entries from arXiv.  Designed to be safe for local
demos: network calls are disabled by default (demo_mode=True).  If you want to
enable live fetching, set demo_mode=False and ensure `feedparser` is installed.

This module never includes API keys (arXiv does not require them). Keep demo_mode
enabled for Kaggle / offline runs.
"""

from typing import List, Dict, Optional
import logging
import hashlib
import time

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ArxivFetcher:
    def __init__(self, demo_mode: bool = True):
        """
        demo_mode: when True, returns mock entries suitable for offline demos.
        """
        self.demo_mode = demo_mode

    def _make_safe_id(self, raw_id: str) -> str:
        """Create a short filesystem-safe id from arXiv id/link."""
        key = str(raw_id) + str(time.time())
        return "arxiv_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]

    def fetch_latest(self, query: str = "all:exoplanet", max_results: int = 5) -> List[Dict]:
        """
        Fetch recent arXiv entries for a query.

        Returns a list of normalized dicts:
          {"id": str, "title": str, "source": "arxiv", "raw": str}

        Notes:
          - Keep demo_mode=True unless you explicitly want live network calls.
          - To enable live fetch: pip install feedparser and call with demo_mode=False.
        """
        if self.demo_mode:
            logger.debug("ArxivFetcher: demo_mode enabled — returning mock entries.")
            return self._mock_entries()

        try:
            import feedparser  # type: ignore # local import to avoid a hard dependency in demo
        except Exception as e:
            logger.error("ArxivFetcher: feedparser not installed (%s). Falling back to mock.", e)
            return self._mock_entries()

        url = f"http://export.arxiv.org/api/query?search_query={query}&max_results={max_results}"
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            logger.exception("ArxivFetcher: failed to fetch or parse feed: %s", e)
            return self._mock_entries()

        items: List[Dict] = []
        entries = getattr(feed, "entries", []) or []
        for entry in entries:
            entry_id = getattr(entry, "id", None) or getattr(entry, "link", None) or str(time.time())
            title = getattr(entry, "title", "arXiv Entry")
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            raw_text = f"{title}\n\n{summary}"
            safe_id = self._make_safe_id(entry_id)
            items.append({"id": safe_id, "title": title, "source": "arxiv", "raw": raw_text})

        logger.info("ArxivFetcher: fetched %d entries from arXiv", len(items))
        return items

    def _mock_entries(self) -> List[Dict]:
        """Return a couple of synthetic entries for offline testing."""
        example = {
            "id": "arxiv_demo_1",
            "title": "Mock arXiv: Example Exoplanet Study",
            "source": "arxiv_mock",
            "raw": (
                "Mock abstract: We report a transit detection of a temperate exoplanet. "
                "Measurements indicate a radius of ~1.8 Earth radii and an orbital period of 14.7 days. "
                "Analysis used transit photometry and simple atmospheric retrieval."
            ),
        }
        return [example]

    # convenience alias
    fetch = fetch_latest


# CLI quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = ArxivFetcher(demo_mode=True)
    results = fetcher.fetch_latest()
    print(f"Fetched {len(results)} entry(ies). Sample:")
    for r in results:
        print("- id:", r["id"])
        print("  title:", r["title"])
        print("  raw (first 120 chars):", (r["raw"] or "")[:120])
