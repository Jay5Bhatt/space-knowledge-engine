# agents/fetcher_agent.py

import os
import glob
import logging
import hashlib
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class FetcherAgent:
    """
    Fetch raw content for the pipeline.

    Default mode (demo):
        - Reads local sample files from data/samples
        - Returns a small mock NASA item
        - Does NOT call any external API

    This keeps the project fully offline, reproducible, and safe for Kaggle judging.
    """

    def __init__(self, samples_dir: str = "data/samples", demo_mode: bool = True):
        self.samples_dir = samples_dir
        self.demo_mode = demo_mode

    # ---------------------------------------------------------
    # Local file ingestion (used in the demo)
    # ---------------------------------------------------------
    def _fetch_local_samples(self) -> List[Dict]:
        items = []
        if not os.path.exists(self.samples_dir):
            logger.warning("Samples directory not found: %s", self.samples_dir)
            return items

        pattern = os.path.join(self.samples_dir, "*")
        for path in sorted(glob.glob(pattern)):
            if os.path.isdir(path):
                continue
            if not path.lower().endswith((".txt", ".md")):
                continue

            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = f.read()
            except Exception as e:
                logger.exception("Failed to read %s: %s", path, e)
                continue

            file_id = os.path.basename(path)
            title = file_id.rsplit(".", 1)[0]

            items.append({
                "id": file_id,
                "title": title,
                "source": "local_file",
                "raw": raw
            })

        logger.info("Loaded %d local sample(s)", len(items))
        return items

    # ---------------------------------------------------------
    # Optional arXiv fetcher (disabled in demo)
    # ---------------------------------------------------------
    def fetch_from_arxiv(self, query: str = "all:exoplanet", max_results: int = 5) -> List[Dict]:
        if self.demo_mode:
            return []

        # Example instructions (do not enable by default):
        #
        # import feedparser
        # url = f"http://export.arxiv.org/api/query?search_query={query}&max_results={max_results}"
        # feed = feedparser.parse(url)
        # items = [...]
        #
        return []

    # ---------------------------------------------------------
    # Optional NASA APOD fetcher (mocked in demo)
    # ---------------------------------------------------------
    def fetch_from_nasa_apod(self) -> List[Dict]:
        if self.demo_mode:
            return [{
                "id": "nasa_apod_mock",
                "title": "Mock NASA APOD",
                "source": "nasa_apod_mock",
                "raw": "Mock NASA APOD content used for offline demonstrations."
            }]

        # Real logic requires:
        # - NASA_API_KEY in environment
        # - requests library
        #
        return []

    # ---------------------------------------------------------
    # Main fetch method
    # ---------------------------------------------------------
    def run(self, sources: Optional[List[str]] = None) -> List[Dict]:
        if sources is None:
            sources = ["local"]

        results = []

        for src in sources:
            if src == "local":
                results.extend(self._fetch_local_samples())
            elif src == "arxiv":
                results.extend(self.fetch_from_arxiv())
            elif src == "nasa_apod":
                results.extend(self.fetch_from_nasa_apod())
            else:
                logger.warning("Unknown source: %s", src)

        # Deduplicate by id
        unique = []
        seen = set()
        for item in results:
            iid = item.get("id")
            if iid not in seen:
                seen.add(iid)
                unique.append(item)

        logger.info("Returning %d unique items", len(unique))
        return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = FetcherAgent()
    data = agent.run(sources=["local", "nasa_apod"])
    print(f"Fetched {len(data)} items")
