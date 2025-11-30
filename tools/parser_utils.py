# tools/parser_utils.py
"""
Small text parsing utilities used by AnalyzerAgent and other components.

This module intentionally uses only standard library functions so it remains
lightweight and fully offline. Functions are focused on common cleaning and
simple sentence splitting useful for short scientific abstracts.
"""

import re
from typing import List

# Normalize repeated whitespace (tabs, newlines -> single space)
_WS_RE = re.compile(r"\s+")
# Simple sentence splitter (keeps punctuation)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\?\!])\s+")


def clean_text(text: str) -> str:
    """
    Basic cleanup for raw text:
      - ensure str (handles None)
      - normalize whitespace to single spaces
      - strip surrounding whitespace

    Keeps punctuation and case intact (downstream components decide on casing).
    """
    if not text:
        return ""
    # Replace common non-printables and control characters
    text = text.replace("\r", " ").replace("\t", " ")
    # Collapse whitespace
    text = _WS_RE.sub(" ", text)
    return text.strip()


def normalize_whitespace(text: str) -> str:
    """
    Alias for clean_text for readability in other modules.
    """
    return clean_text(text)


def extract_sentences(text: str) -> List[str]:
    """
    Naive sentence splitter:
      - splits on '.', '?', '!' followed by whitespace
      - strips results and filters out very short fragments

    For more accurate results, integrate an NLP sentence tokenizer later.
    """
    if not text:
        return []
    cleaned = clean_text(text)
    parts = [s.strip() for s in _SENTENCE_SPLIT_RE.split(cleaned) if s.strip()]
    return parts


def first_n_sentences(text: str, n: int = 2) -> str:
    """
    Return the first n sentences joined by a space. If there are fewer than n,
    return the available text (trimmed).
    """
    sents = extract_sentences(text)
    if not sents:
        return ""
    return " ".join(sents[:n]).strip()


def remove_urls(text: str) -> str:
    """
    Strip common URL patterns from text to avoid noisy tokens in analysis.
    """
    if not text:
        return ""
    # very simple URL pattern
    url_re = re.compile(r"https?://\S+|www\.\S+")
    return url_re.sub("", text).strip()


def truncate(text: str, max_chars: int = 400) -> str:
    """
    Safely truncate text to max_chars without cutting in the middle of a word.
    """
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    # try to cut at last space before limit
    cut = text[: max_chars - 1]
    last_space = cut.rfind(" ")
    if last_space > 0:
        return cut[:last_space].rstrip() + "..."
    return cut.rstrip() + "..."
