# run_demo.py
"""
One-shot demo for the Space Knowledge Engine.

Behavior:
- Loads environment from .env
- If GEMINI_API_KEY present -> enables Gemini summarizer
- If NASA_API_KEY or feed access present -> enables live tools for fetch (safe fallbacks to mock)
- Always includes local samples in the fetch pipeline
- Writes JSON to data/demo_outputs/readme_demo_output.json
"""

import json
import os
import logging
from typing import List, Dict, Any

from dotenv import load_dotenv
load_dotenv()  # loads .env into environment

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import core orchestrator and fallback agent classes
from agents.orchestrator_agent import OrchestratorAgent
from agents.summarizer_agent import SummarizerAgent
from agents.evaluator_agent import EvaluatorAgent

# Tools (live wrappers with demo_mode flag)
from tools.arxiv_fetcher import ArxivFetcher
from tools.nasa_api import NasaApi

# Optional: access original FetcherAgent to reuse local-sample loader if available
try:
    from agents.fetcher_agent import FetcherAgent
except Exception:
    FetcherAgent = None


def make_live_fetcher_wrapper(original_fetcher) -> callable:
    """
    Return a function that will fetch:
      - local samples (if supported by original_fetcher)
      - arXiv (live if demo_mode False, otherwise mock)
      - NASA APOD (live if demo_mode False, otherwise mock)

    This function is assigned to orchestrator.fetcher.run so the orchestrator
    uses live data without modifying FetcherAgent class.
    """
    arxiv_tool = ArxivFetcher(demo_mode=False)   # will fall back to mock if feedparser missing
    nasa_tool = NasaApi(demo_mode=False)        # will fall back to mock if key missing or requests missing

    def _local_samples() -> List[Dict[str, Any]]:
        # Prefer using the internal helper if it exists
        if original_fetcher and hasattr(original_fetcher, "_fetch_local_samples"):
            try:
                return original_fetcher._fetch_local_samples()
            except Exception:
                pass

        # fallback: read files from data/samples/*.txt
        items = []
        samples_dir = "data/samples"
        if os.path.exists(samples_dir):
            for fname in os.listdir(samples_dir):
                if fname.endswith(".txt"):
                    path = os.path.join(samples_dir, fname)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            raw = f.read()
                        items.append({
                            "id": fname,
                            "title": f"Local Sample: {fname}",
                            "source": "local_file",
                            "raw": raw,
                        })
                    except Exception:
                        continue
        return items

    def run() -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        # 1) local samples
        results.extend(_local_samples())

        # 2) arXiv (may return mock if network/tools missing)
        try:
            arxiv_items = arxiv_tool.fetch_latest(max_results=5)
            if arxiv_items:
                results.extend(arxiv_items)
        except Exception:
            logger.exception("ArXiv fetch failed, continuing with local samples.")

        # 3) NASA APOD (may return mock)
        try:
            apod = nasa_tool.fetch_apod()
            if apod:
                results.append(apod)
        except Exception:
            logger.exception("NASA fetch failed, continuing.")

        # Deduplicate by id
        seen = set()
        unique = []
        for r in results:
            rid = r.get("id") or (r.get("title") or "")[:60]
            if rid in seen:
                continue
            seen.add(rid)
            unique.append(r)
        logger.info("Live fetcher returning %d unique items", len(unique))
        return unique

    return run


def main():
    out_path = "data/demo_outputs/readme_demo_output.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Create default orchestrator
    orchestrator = OrchestratorAgent()

    # ------------- Replace fetcher.run with a wrapper that uses live tools -------------
    try:
        original_fetcher = getattr(orchestrator, "fetcher", None)
        live_run = make_live_fetcher_wrapper(original_fetcher)
        # monkeypatch the fetcher run function used by the orchestrator
        orchestrator.fetcher.run = live_run
        logger.info("Orchestrator fetcher replaced with live fetcher wrapper.")
    except Exception:
        logger.exception("Failed to attach live fetcher wrapper; continuing with default fetcher.")

    # ------------- Optionally enable Gemini summarizer if key present -------------
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        orchestrator.summarizer = SummarizerAgent(use_gemini=True)
        logger.info("Gemini summarizer enabled (GEMINI_API_KEY present).")
    else:
        orchestrator.summarizer = SummarizerAgent(use_gemini=False)
        logger.info("Using local summarizer (no GEMINI_API_KEY).")

    # ------------- Optionally lower evaluator threshold for testing -------------
    # Default in EvaluatorAgent is likely 3.0 — lowering helps process demo items.
    try:
        orchestrator.evaluator = EvaluatorAgent(threshold=1.0)
        logger.info("Evaluator threshold set to 1.0 for demo (adjustable).")
    except Exception:
        logger.exception("Failed to adjust evaluator threshold.")

    # ------------- Run one cycle -------------
    try:
        summary = orchestrator.run_once()
    except Exception as e:
        logger.exception("Demo run failed: %s", e)
        summary = {"error": str(e)}

    # ------------- Write stable demo file -------------
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"Demo complete. Summary written to {out_path}")
    except Exception as e:
        logger.exception("Failed to write demo output file: %s", e)
        print("Demo finished but failed to write demo output.")


if __name__ == "__main__":
    main()
