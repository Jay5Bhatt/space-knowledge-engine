# agents/evaluator_agent.py
"""
EvaluatorAgent (production-ready)

Responsibilities
- Score analyzed items (the output of AnalyzerAgent) using configurable heuristics.
- Return detailed score breakdown, human-readable reasons, and a boolean `passed_threshold`.
- Provide batch evaluation helpers and a small CLI demo.

Design goals
- Deterministic, transparent scoring (no hidden ML).
- Configurable weights and thresholds so judges can see the logic.
- Lightweight and dependency-free for easy demo and grading.

Expected input (analysis_item):
{
  "original_id": str,
  "title": str,
  "source": str,
  "analysis": {
      "word_count": int,
      "sentence_count": int,
      "numbers_found": [float, ...],
      "measurements": [{"value": float, "unit": str, "raw": str}, ...],
      "keywords_detected": [str, ...],
      "claims": [str, ...],
      "snippet": str
  }
}

Output (per item):
{
  "original_id": str,
  "score": float,
  "passed_threshold": bool,
  "reasons": [str, ...],
  "breakdown": { "keyword_score": float, "numeric_score": float, ... }
}
"""

from __future__ import annotations

import logging
from typing import Dict, List, Iterable, Any, Optional
import math

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class EvaluatorAgent:
    """
    EvaluatorAgent scores AnalyzerAgent outputs.

    Parameters
    ----------
    threshold: float
        Minimum total score required to pass.
    weights: Optional[Dict[str, float]]
        Weights for individual heuristics (keyword, numeric, length, claims).
    """

    DEFAULT_WEIGHTS = {
        "keyword": 2.0,       # points per keyword detected
        "numeric_bonus": 3.0, # bonus if numeric density passes threshold
        "length_bonus": 1.0,  # small bonus for content length
        "claim_bonus": 1.5,   # points per strong claim detected
    }

    def __init__(self, threshold: float = 3.0, weights: Optional[Dict[str, float]] = None):
        self.threshold = float(threshold)
        w = dict(self.DEFAULT_WEIGHTS)
        if weights:
            w.update(weights)
        self.weights = w

        # heuristic parameters (tunable)
        self.numeric_count_for_bonus = 2      # need > 2 numbers to award numeric_bonus
        self.min_word_count_for_length_bonus = 20
        self.min_claim_length_for_bonus = 1   # claims list already filters by length in analyzer

    def score(self, analysis_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a single analyzed item.

        Returns:
            {
              "original_id": str,
              "score": float,
              "passed_threshold": bool,
              "reasons": [...],
              "breakdown": {...}
            }
        """
        analysis = analysis_item.get("analysis", {}) if analysis_item else {}
        wc = int(analysis.get("word_count", 0))
        numbers = analysis.get("numbers_found", []) or []
        measurements = analysis.get("measurements", []) or []
        keywords = analysis.get("keywords_detected", []) or []
        claims = analysis.get("claims", []) or []

        reasons: List[str] = []
        breakdown: Dict[str, float] = {}

        # Keyword score: linear with number of keywords found
        keyword_pts = len(keywords) * float(self.weights.get("keyword", 2.0))
        breakdown["keyword_score"] = keyword_pts
        if len(keywords) > 0:
            reasons.append(f"Keywords detected: {len(keywords)} (+{keyword_pts:.1f})")

        # Numeric/data density bonus
        numeric_pts = 0.0
        if len(numbers) > self.numeric_count_for_bonus:
            numeric_pts = float(self.weights.get("numeric_bonus", 3.0))
            reasons.append(f"Numeric density high ({len(numbers)} numbers) (+{numeric_pts:.1f})")
        breakdown["numeric_score"] = numeric_pts

        # Measurement presence (structured scientific values) adds small points
        measurement_pts = 0.0
        if len(measurements) > 0:
            measurement_pts = min(len(measurements) * 0.5, 3.0)  # capped incremental bonus
            reasons.append(f"Measurements found: {len(measurements)} (+{measurement_pts:.1f})")
        breakdown["measurement_score"] = measurement_pts

        # Content length heuristic
        length_pts = 0.0
        if wc >= self.min_word_count_for_length_bonus:
            length_pts = float(self.weights.get("length_bonus", 1.0))
            breakdown["length_score"] = length_pts
            reasons.append(f"Content length sufficient ({wc} words) (+{length_pts:.1f})")
        else:
            breakdown["length_score"] = length_pts
            reasons.append(f"Short content ({wc} words) (no length bonus)")

        # Claims heuristic: each strong claim adds points
        claim_pts = min(len(claims) * float(self.weights.get("claim_bonus", 1.5)), 6.0)
        if claim_pts > 0:
            reasons.append(f"Claims detected: {len(claims)} (+{claim_pts:.1f})")
        breakdown["claim_score"] = claim_pts

        # Penalty for extremely short or likely noisy items
        penalty = 0.0
        if wc < 6:
            penalty = -2.0
            reasons.append("Very short content; penalized (-2.0)")
        breakdown["penalty"] = penalty

        # Total score
        total_score = keyword_pts + numeric_pts + measurement_pts + length_pts + claim_pts + penalty

        # Normalize tiny negative values to zero floor when appropriate (optional)
        # total_score = max(total_score, -10.0)

        passed = total_score >= self.threshold

        result = {
            "original_id": analysis_item.get("original_id"),
            "score": float(round(total_score, 3)),
            "passed_threshold": bool(passed),
            "reasons": reasons,
            "breakdown": breakdown,
            "raw_analysis": analysis,  # include for auditability (judges can inspect)
        }
        return result

    def evaluate_batch(self, items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate a batch (iterable) of analyzed items and return scored results.
        """
        scored = []
        for it in items:
            try:
                s = self.score(it)
                scored.append(s)
            except Exception as e:
                logger.exception("EvaluatorAgent: error scoring item %s: %s", it.get("original_id", "<n/a>"), e)
        logger.info("EvaluatorAgent: scored %d items", len(scored))
        return scored

    def filter_passed(self, scored_items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Return only items that passed the threshold.
        """
        return [s for s in scored_items if s.get("passed_threshold")]

    def summary_metrics(self, scored_items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute simple metrics for a scored batch (mean score, pass rate).
        """
        items = list(scored_items)
        if not items:
            return {"count": 0, "mean_score": 0.0, "pass_rate": 0.0}
        total = sum(float(it.get("score", 0.0)) for it in items)
        mean_score = total / len(items)
        passed = sum(1 for it in items if it.get("passed_threshold"))
        pass_rate = passed / len(items)
        return {"count": len(items), "mean_score": round(mean_score, 3), "pass_rate": round(pass_rate, 3)}

# -------------------------
# Quick CLI demo
# -------------------------
if __name__ == "__main__":
    logging = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    # Example synthetic analysis item (matches AnalyzerAgent output)
    example_analysis_item = {
        "original_id": "example1.txt",
        "title": "K2-18b water detection",
        "source": "local_sample",
        "analysis": {
            "word_count": 58,
            "sentence_count": 5,
            "numbers_found": [124.0, 2.6, 33.0, 8.0],
            "measurements": [
                {"value": 124.0, "unit": "light-years", "raw": "124 light-years"},
                {"value": 2.6, "unit": "Earth", "raw": "2.6 times that of Earth"},
                {"value": 33.0, "unit": "days", "raw": "33 days"},
            ],
            "keywords_detected": ["exoplanet", "radius", "transit"],
            "claims": [
                "Spectral analysis revealed signatures consistent with water vapor",
                "The planet has a radius of approximately 2.6 times that of Earth"
            ],
            "snippet": "Title: Discovery of Water Vapor on K2-18b. The exoplanet K2-18b..."
        }
    }

    evaluator = EvaluatorAgent()
    scored = evaluator.score(example_analysis_item)
    import json
    print(json.dumps(scored, indent=2))
    # Batch demo
    batch = evaluator.evaluate_batch([example_analysis_item])
    print("Batch metrics:", evaluator.summary_metrics(batch))
