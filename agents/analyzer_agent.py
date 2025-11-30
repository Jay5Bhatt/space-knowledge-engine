# agents/analyzer_agent.py
"""
AnalyzerAgent (production-ready)

Responsibilities
- Convert raw text into structured analysis suitable for downstream agents:
  word counts, numeric/measurement extraction, keyword detection, short "claims",
  and a compact snippet for summarization.

Design goals
- Deterministic, low-dependency, safe for offline demo mode.
- Easy to extend with PDF parsing (pypdf), scientific table/parsing libraries,
  or NLP models for richer entity extraction.
- Clear, typed inputs and outputs so downstream agents (Evaluator, Memory, Summarizer)
  can consume the results easily.

Expected input item format (dict):
{
  "id": "<unique id, e.g. filename or url>",
  "title": "<optional title>",
  "source": "<source marker (local_file, arxiv, nasa, etc)>",
  "raw": "<raw text content>"
}

Output (per item) - analysis dict keys:
{
  "original_id": str,
  "word_count": int,
  "sentence_count": int,
  "numbers_found": List[float],
  "measurements": List[{"value": float, "unit": str, "raw": str}],
  "keywords_detected": List[str],
  "claims": List[str],          # short sentences that likely contain core facts
  "snippet": str               # compact text for summarization
}

Notes:
- This module intentionally avoids heavy NLP dependencies to keep the demo reproducible.
- To add advanced NLP (NER, dependency parsing), integrate spaCy or transformer models in future work.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Iterable, Optional, Any
import sys
import os

# Make sure tools package can be imported when executed from repo root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from tools.parser_utils import clean_text  # lightweight normalizer
except Exception:
    # Fallback: define a minimal clean_text if tools import fails
    def clean_text(s: str) -> str:
        if not s:
            return ""
        return " ".join(s.split())

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# --- Helper regex patterns (science-oriented) ---
# Matches floats and integers (captures signs, decimals)
_NUMBER_RE = re.compile(r"[-+]?\d*\.\d+|\d+")
# Basic measurement capture: value + unit (e.g., '2.6 Earth radii', '33 days', '1e3 km')
_MEASUREMENT_RE = re.compile(
    r"(?P<raw>(?P<value>[-+]?\d*\.\d+|\d+(?:e[-+]?\d+)?)[\s\-]*(?P<unit>[A-Za-z/%°μkmhdys]+))",
    flags=re.IGNORECASE,
)
# Sentence splitter (naive)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\?\!])\s+")


class AnalyzerAgent:
    """
    AnalyzerAgent - production-ready analyzer for scientific text.

    Parameters
    ----------
    keywords: Optional[Iterable[str]]
        Domain keywords to detect (case-insensitive). If None, a sensible default list is used.
    min_claim_length: int
        Minimum characters for a sentence to be considered a 'claim'.
    max_snippet_chars: int
        Length of snippet to produce for summarizers.
    """

    DEFAULT_KEYWORDS = [
        "exoplanet",
        "orbital",
        "orbit",
        "radius",
        "mass",
        "transit",
        "spectra",
        "spectrum",
        "atmosphere",
        "cme",
        "solar",
        "habitability",
        "habitable",
        "apparent magnitude",
        "period",
        "days",
        "light-years",
        "spectroscopy",
    ]

    def __init__(
        self,
        keywords: Optional[Iterable[str]] = None,
        min_claim_length: int = 30,
        max_snippet_chars: int = 400,
    ):
        self.keywords = [k.lower() for k in (list(keywords) if keywords else self.DEFAULT_KEYWORDS)]
        self.min_claim_length = min_claim_length
        self.max_snippet_chars = max_snippet_chars

    # -------------------------
    # Low-level extractors
    # -------------------------
    def _extract_numbers(self, text: str) -> List[float]:
        """Return numeric tokens found in text as floats (best-effort)."""
        vals: List[float] = []
        for m in _NUMBER_RE.findall(text):
            try:
                vals.append(float(m))
            except Exception:
                # ignore parsing errors for odd formats
                continue
        return vals

    def _extract_measurements(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract (value, unit, raw) using a measurement regex.
        Example matches: '2.6 Earth radii', '33 days', '124 light-years'
        """
        results = []
        for m in _MEASUREMENT_RE.finditer(text):
            try:
                raw = m.group("raw")
                val_str = m.group("value")
                unit = m.group("unit").strip()
                # Normalize common unit tokens (simple)
                unit = unit.replace("μ", "u")
                value = float(val_str)
                results.append({"value": value, "unit": unit, "raw": raw})
            except Exception:
                # Skip if conversion fails
                continue
        return results

    def _find_keywords(self, text: str) -> List[str]:
        """Return the list of configured keywords found in the text (case-insensitive)."""
        found = []
        lower = text.lower()
        for kw in self.keywords:
            if kw in lower:
                found.append(kw)
        return found

    def _extract_sentences(self, text: str) -> List[str]:
        """A simple sentence splitter; replace with NLP sentence tokenizer for more accuracy."""
        if not text:
            return []
        # split on punctuation followed by whitespace
        sents = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
        return sents

    def _find_claims(self, text: str) -> List[str]:
        """
        Heuristic: return sentences that contain at least one keyword or a measurement
        and are longer than min_claim_length. These are candidate 'claims' suitable for summaries.
        """
        sents = self._extract_sentences(text)
        claims = []
        for s in sents:
            if len(s) < self.min_claim_length:
                continue
            if _MEASUREMENT_RE.search(s) or any(kw in s.lower() for kw in self.keywords):
                claims.append(s)
        return claims

    # -------------------------
    # Public analysis API
    # -------------------------
    def analyze_text(self, raw_text: str) -> Dict[str, Any]:
        """
        Produce analysis for a block of text.
        Returned structure is intentionally JSON-serializable and concise.
        """
        cleaned = clean_text(raw_text or "")
        word_count = len(cleaned.split())
        sentences = self._extract_sentences(cleaned)
        sentence_count = len(sentences)
        numbers = self._extract_numbers(cleaned)
        measurements = self._extract_measurements(cleaned)
        keywords = self._find_keywords(cleaned)
        claims = self._find_claims(cleaned)
        snippet = cleaned[: self.max_snippet_chars] + ("..." if len(cleaned) > self.max_snippet_chars else "")

        analysis = {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "numbers_found": numbers,
            "measurements": measurements,
            "keywords_detected": keywords,
            "claims": claims,
            "snippet": snippet,
        }
        return analysis

    def run_on_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single item dict and return a new dict containing:
        - original_id
        - title (if present)
        - source (if present)
        - analysis (the analysis dict)
        """
        raw = item.get("raw", "") or ""
        analysis = self.analyze_text(raw)
        out = {
            "original_id": item.get("id"),
            "title": item.get("title"),
            "source": item.get("source"),
            "analysis": analysis,
        }
        return out

    def run(self, items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze an iterable of items and return a list of analysis results.
        """
        results = []
        for it in items:
            try:
                res = self.run_on_item(it)
                results.append(res)
            except Exception as e:
                logger.exception("AnalyzerAgent: error analyzing item %s: %s", it.get("id"), str(e))
        logger.info("AnalyzerAgent: processed %d items", len(results))
        return results


# -------------------------
# Quick CLI demo (local)
# -------------------------
if __name__ == "__main__":
    logging = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    sample_text = (
        "Title: Discovery of Water Vapor on K2-18b. "
        "The exoplanet K2-18b, located 124 light-years away, was observed using Hubble. "
        "Spectral analysis revealed signatures consistent with water vapor. "
        "The planet has a radius of approximately 2.6 times that of Earth and an orbital period of 33 days. "
        "Methods included transit spectroscopy over 8 transits."
    )

    analyzer = AnalyzerAgent()
    item = {"id": "example1.txt", "title": "K2-18b water detection", "raw": sample_text, "source": "local_sample"}
    out = analyzer.run_on_item(item)
    import json
    print(json.dumps(out, indent=2))
