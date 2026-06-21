"""
Language detector for English (en), French (fr), and Haitian Creole (ht).

Strategy
--------
1. Apply a lightweight Haitian Creole keyword heuristic first (since most
   off-the-shelf language detectors have weak or no support for 'ht').
2. Fall back to langdetect for en/fr/other.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from langdetect import detect, LangDetectException  # type: ignore
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not installed — language detection degraded.")

# ── Haitian Creole heuristics ─────────────────────────────────────────────────
# Common Haitian Creole function words / markers that are absent / rare in French
_HT_MARKERS = re.compile(
    r"\b(m|w|li|nou|yo|pa|nan|ak|pou|sou|bay|bèl|mèsi|"
    r"avèk|depi|menm|jan|lè|toujou|anko|konsa|gade|wè|"
    r"Ayiti|ayisyen|ayisyèn|peyi\s*a|gouvènman|prezidan|"
    r"kriz|sekirite|lapolis|gang|vyolans|ekonomi|pòvrete|"
    r"grangou|lopital|lekòl|elektrisite|dlo|wout|jwenn|rele|"
    r"Bondye|blan|nwa|pitit|fanmi|zanmi|frè|sè)\b",
    re.IGNORECASE,
)

# Minimum fraction of HT-marker words to classify as Haitian Creole
_HT_THRESHOLD = 0.06


def detect_language(text: str) -> str:
    """
    Return ISO 639-1 code: 'en', 'fr', 'ht', or 'unknown'.
    """
    if not text or not text.strip():
        return "unknown"

    cleaned = text.strip()

    # Step 1: Haitian Creole heuristic
    words = re.findall(r"\b\w+\b", cleaned)
    if words:
        ht_hits = len(_HT_MARKERS.findall(cleaned))
        ratio = ht_hits / len(words)
        if ratio >= _HT_THRESHOLD:
            return "ht"

    # Step 2: langdetect
    if _LANGDETECT_AVAILABLE:
        try:
            lang = detect(cleaned)
            if lang in ("en", "fr"):
                return lang
            # Creole sometimes misclassified as Portuguese or Spanish
            if lang in ("pt", "es", "ca"):
                # Re-check with slightly lower threshold
                words2 = re.findall(r"\b\w+\b", cleaned)
                if words2:
                    ht_hits2 = len(_HT_MARKERS.findall(cleaned))
                    if ht_hits2 / len(words2) >= 0.03:
                        return "ht"
            return lang[:2] if lang else "unknown"
        except LangDetectException:
            pass

    # Step 3: simple character-frequency heuristic (en vs fr)
    accented = len(re.findall(r"[àâäéèêëîïôùûüç]", cleaned.lower()))
    if accented / max(len(cleaned), 1) > 0.05:
        return "fr"
    return "en"


def is_relevant_language(lang: str) -> bool:
    """Return True if the language is one we analyse (en, fr, ht)."""
    return lang in ("en", "fr", "ht")
