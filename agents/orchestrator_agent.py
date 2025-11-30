# agents/orchestrator_agent.py
"""
OrchestratorAgent

Coordinates the full pipeline:
  Fetch -> Analyze -> Evaluate -> Summarize -> Memory
Reads environment to decide whether to enable Gemini / real NASA calls.
Writes per-run JSON logs to data/demo_outputs/ and a session_state.json file.
"""

from __future__ import annotations

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
load_dotenv()

from agents.fetcher_agent import FetcherAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.evaluator_agent import EvaluatorAgent
from agents.summarizer_agent import SummarizerAgent
from agents.memory_agent import MemoryAgent

from tools.nasa_api import NasaApi  # ensure tools is a package or on PYTHONPATH

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class OrchestratorAgent:
    def __init__(self, output_dir: str = "data/demo_outputs"):
        """
        output_dir: where run logs and session state are written.
        NASA demo mode and Gemini usage are controlled via environment variables:
          - NASA_DEMO_MODE (true/1/yes => use demo mocks)
          - GEMINI_API_KEY (if present, SummarizerAgent will attempt Gemini)
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # decide NASA demo mode from env (default: False -> try real API)
        nasa_demo_env = os.getenv("NASA_DEMO_MODE", "").strip().lower()
        nasa_demo_mode = nasa_demo_env in ("1", "true", "yes")

        # decide if we should instruct summarizer to try Gemini (it will fallback if no key)
        use_gemini = bool(os.getenv("GEMINI_API_KEY"))

        # instantiate agents
        # Pass a NASA client instance into FetcherAgent if your fetcher accepts it.
        self.nasa_client = NasaApi(demo_mode=nasa_demo_mode)
        try:
            # Try to configure FetcherAgent with tool clients if its constructor supports them.
            self.fetcher = FetcherAgent(nasa_client=self.nasa_client, arxiv_demo=True)
        except TypeError:
            # Fallback if FetcherAgent has a different signature
            self.fetcher = FetcherAgent()

        self.analyzer = AnalyzerAgent()
        self.evaluator = EvaluatorAgent()
        self.summarizer = SummarizerAgent(use_gemini=use_gemini)
        self.memory = MemoryAgent(storage_path="data/memory.json")

        # session file path for pause/resume / long-running metadata
        self.session_path = os.path.join(self.output_dir, "session_state.json")

    # -----------------------
    # Run helpers
    # -----------------------
    def run_once(self) -> Dict[str, Any]:
        """
        Execute one full cycle. Returns a summary dict and writes a JSON log.
        """
        logger.info("=== Starting Orchestrator Cycle ===")
        run_start = datetime.utcnow().isoformat() + "Z"

        # Fetch
        items = self.fetcher.run()
        logger.info("Fetched %d item(s).", len(items))

        run_log: Dict[str, Any] = {
            "timestamp": run_start,
            "steps": [f"Fetched {len(items)} items"],
            "processed_items": 0,
            "items": []
        }

        processed = 0
        for it in items:
            item_id = it.get("id", "<no-id>")
            try:
                analysis_wrapper = self.analyzer.run_on_item(it)
                score = self.evaluator.score(analysis_wrapper)
                entry_log: Dict[str, Any] = {
                    "id": item_id,
                    "title": it.get("title"),
                    "score": score.get("score"),
                    "passed": score.get("passed_threshold", False),
                }

                if not entry_log["passed"]:
                    logger.info("Skipped: %s (score=%s)", item_id, entry_log["score"])
                    run_log["items"].append(entry_log)
                    continue

                summary_text = self.summarizer.summarize(it, analysis_wrapper["analysis"])

                # Store in memory (store raw initially; MemoryAgent.compact can trim later)
                self.memory.store(item_id, {
                    "raw": it.get("raw"),
                    "analysis": analysis_wrapper["analysis"],
                    "evaluation": score,
                    "summary": summary_text,
                })

                entry_log.update({"summary": summary_text})
                processed += 1
                logger.info("Processed & stored: %s (score=%s)", item_id, entry_log["score"])
                run_log["items"].append(entry_log)

            except Exception as exc:
                logger.exception("Error processing item %s: %s", item_id, exc)
                run_log["items"].append({"id": item_id, "error": str(exc)})

        # Post-run housekeeping
        self.memory.compact()
        run_log["processed_items"] = processed
        run_id = self._save_log(run_log)

        # update session state
        self._update_session_state(last_run=run_id, last_timestamp=run_start, processed=processed)
        logger.info("Cycle complete. Log saved to %s", run_id)
        return run_log

    def run_continuous(self, iterations: int = 10, interval_s: int = 30):
        """
        Run multiple cycles with a pause interval. Updates session_state.json between runs.
        """
        session = {"iterations_requested": iterations, "runs": 0, "total_processed": 0}
        for i in range(iterations):
            logger.info("Starting iteration %d/%d", i + 1, iterations)
            result = self.run_once()
            session["runs"] += 1
            session["total_processed"] += result.get("processed_items", 0)
            # save session snapshot
            with open(self.session_path, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2)
            if i < iterations - 1:
                time.sleep(interval_s)
        logger.info("Continuous run finished: %s", session)
        return session

    # -----------------------
    # Persistence helpers
    # -----------------------
    def _save_log(self, run_data: Dict[str, Any]) -> str:
        run_name = f"run_{int(time.time())}.json"
        path = os.path.join(self.output_dir, run_name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run_data, f, indent=2)
        return path

    def _update_session_state(self, last_run: str, last_timestamp: str, processed: int):
        state = {}
        if os.path.exists(self.session_path):
            try:
                with open(self.session_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                state = {}

        state.update({
            "last_run": last_run,
            "last_timestamp": last_timestamp,
            "last_processed": processed,
            "modified": datetime.utcnow().isoformat() + "Z",
        })
        with open(self.session_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
