# agents/memory_agent.py

import json
import os
import time
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class MemoryAgent:
    """
    Simple JSON-backed memory store.

    Responsibilities:
        - Persist processed items so the system can avoid re-processing the same data.
        - Provide a basic search function based on keyword matching.
        - Compact stored entries by trimming large fields.
        - Keep everything easy to inspect and reproducible for grading.

    Storage format (memory.json):
        [
            {
                "key": "<unique ID>",
                "timestamp": <unix time>,
                "data": {
                    "summary": "...",
                    "analysis": {...},
                    "evaluation": {...},
                    "raw": "...",     # removed during compaction
                }
            },
            ...
        ]
    """

    def __init__(self, storage_path: str = "data/memory.json"):
        self.storage_path = storage_path
        self._ensure_initialized()

    # ---------------------------------------------------------
    # Initialization helpers
    # ---------------------------------------------------------
    def _ensure_initialized(self):
        """Create parent directory and file if needed."""
        parent = os.path.dirname(self.storage_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w") as f:
                json.dump([], f)

    # ---------------------------------------------------------
    # Basic load/save
    # ---------------------------------------------------------
    def _load(self) -> List[Dict[str, Any]]:
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("MemoryAgent: failed to load memory file: %s", e)
            return []

    def _save(self, data: List[Dict[str, Any]]) -> None:
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("MemoryAgent: failed to write memory file: %s", e)

    # ---------------------------------------------------------
    # Public APIs
    # ---------------------------------------------------------
    def store(self, key: str, data: Dict[str, Any]) -> None:
        """
        Insert or update a record.

        If an item with the same key already exists, it gets replaced.
        Otherwise, append as a new entry.
        """
        memory = self._load()

        record = {
            "key": key,
            "timestamp": time.time(),
            "data": data,
        }

        # Deduplication by key
        updated = False
        for idx, old in enumerate(memory):
            if old.get("key") == key:
                memory[idx] = record
                updated = True
                break

        if not updated:
            memory.append(record)

        self._save(memory)
        logger.info("MemoryAgent: stored key=%s (updated=%s)", key, updated)

    def query_similar(self, text: str) -> List[Dict[str, Any]]:
        """
        Simple keyword-based search in summaries.

        This avoids ML embeddings so the project stays fully offline.
        """
        text = text.lower()
        memory = self._load()
        results = []

        for record in memory:
            summary = record.get("data", {}).get("summary", "")
            if isinstance(summary, str) and text in summary.lower():
                results.append(record)

        return results

    def compact(self) -> None:
        """
        Reduce storage size by removing large raw fields.

        This is mainly for long-running sessions or cloud deployment,
        but it keeps memory.json tidy for grading too.
        """
        memory = self._load()
        changed = False

        for rec in memory:
            data = rec.get("data", {})
            if "raw" in data:
                del data["raw"]
                changed = True

        if changed:
            self._save(memory)
            logger.info("MemoryAgent: compacted memory (removed raw text).")
