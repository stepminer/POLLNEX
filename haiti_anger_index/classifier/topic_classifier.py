"""
Topic classifier for Haitian social-media posts.

Each post is assigned to one or more of the nine topic categories defined
in config.TOPICS using a multilingual keyword matching strategy.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

from haiti_anger_index import config


def _build_patterns() -> dict:
    """Pre-compile regex patterns for every topic."""
    patterns = {}
    for topic_key, topic in config.TOPICS.items():
        combined_kws = (
            topic.get("keywords_en", [])
            + topic.get("keywords_fr", [])
            + topic.get("keywords_ht", [])
        )
        # Escape and join into one alternation pattern
        escaped = [re.escape(kw) for kw in combined_kws if kw]
        if escaped:
            patterns[topic_key] = re.compile(
                r"\b(" + "|".join(escaped) + r")\b",
                re.IGNORECASE,
            )
    return patterns


_TOPIC_PATTERNS = _build_patterns()


def classify_topics(text: str) -> List[str]:
    """
    Return a list of topic keys found in *text*.

    Returns at minimum ['general'] if no specific topic is matched.
    """
    if not text:
        return ["general"]

    matched = [
        key
        for key, pattern in _TOPIC_PATTERNS.items()
        if pattern.search(text)
    ]
    return matched if matched else ["general"]
