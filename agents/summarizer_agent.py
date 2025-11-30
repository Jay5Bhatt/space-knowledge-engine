# agents/summarizer_agent.py

from dotenv import load_dotenv
load_dotenv()  # reads .env in repo root if present

import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SummarizerAgent:
    """
    Produces short summaries for processed items.
    Optionally uses Gemini if GEMINI_API_KEY is set.
    """

    def __init__(self, use_gemini: bool = False):
        self.use_gemini = use_gemini

    def summarize(self, item: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        raw_text = item.get("raw", "") or ""

        if self.use_gemini:
            summary = self._summarize_with_gemini(raw_text)
            if summary:
                return summary
            logger.warning("Gemini not available or failed — falling back to local summarizer.")

        return self._summarize_local(raw_text, analysis)

    def _summarize_local(self, text: str, analysis: Dict[str, Any]) -> str:
        claims: List[str] = analysis.get("claims", []) or []
        keywords: List[str] = analysis.get("keywords_detected", []) or []

        if claims:
            excerpt = " ".join(claims[:2])
        else:
            snippet = analysis.get("snippet", "") or ""
            excerpt = snippet[:200]

        kw = ", ".join(keywords) if keywords else "no key terms detected"
        return f"{excerpt.strip()}\n\n(Key terms: {kw})"

    def _summarize_with_gemini(self, text: str) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.info("GEMINI_API_KEY not present, skipping Gemini.")
            return ""

        try:
            import importlib
            genai = importlib.import_module("google.generativeai")
        except Exception as e:
            logger.error("Gemini library missing: %s", e)
            return ""

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-pro")
            prompt = (
                "Summarize the following space research text in 3–4 sentences, "
                "focusing on the central scientific findings:\n\n"
                f"{text}"
            )
            response = model.generate_content(prompt)
            return response.text.strip() if response and getattr(response, "text", None) else ""
        except Exception as e:
            logger.error("Gemini summarization failed: %s", e)
            return ""
