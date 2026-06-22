"""
Multilingual sentiment classifier.

Uses cardiffnlp/twitter-xlm-roberta-base-sentiment which supports 100+
languages including French.  Haitian Creole is close enough to French that
the model performs well on it.

Falls back to a lightweight keyword-based classifier when transformers is
unavailable (demo / low-resource environments).
"""

import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

try:
    from transformers import pipeline  # type: ignore
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not installed — using keyword-based fallback classifier.")

from haiti_anger_index import config

# Label mapping from model output → canonical labels
_LABEL_MAP = {
    "positive": "POSITIVE",
    "negative": "NEGATIVE",
    "neutral": "NEUTRAL",
    "label_0": "NEGATIVE",
    "label_1": "NEUTRAL",
    "label_2": "POSITIVE",
}


class SentimentClassifier:
    """
    Wraps the XLM-RoBERTa multilingual sentiment model.

    Usage::

        clf = SentimentClassifier()
        results = clf.classify_batch(["I love Haiti", "Violence is terrible"])
        # [('POSITIVE', 0.97), ('NEGATIVE', 0.99)]
    """

    def __init__(self) -> None:
        self._pipe = None
        if _TRANSFORMERS_AVAILABLE:
            try:
                self._pipe = pipeline(
                    "text-classification",
                    model=config.SENTIMENT_MODEL,
                    tokenizer=config.SENTIMENT_MODEL,
                    max_length=config.SENTIMENT_MAX_LENGTH,
                    truncation=True,
                    top_k=1,
                )
                logger.info("Sentiment model loaded: %s", config.SENTIMENT_MODEL)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not load model (%s) — using keyword fallback.", exc)

    # ── Public API ────────────────────────────────────────────────────────────

    def classify(self, text: str) -> Tuple[str, float]:
        """Classify a single text. Returns (label, score)."""
        results = self.classify_batch([text])
        return results[0]

    def classify_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """
        Classify a batch of texts.

        Returns a list of (label, score) tuples where label is one of
        POSITIVE, NEGATIVE, NEUTRAL and score is a confidence in [0, 1].
        """
        if not texts:
            return []

        if self._pipe is not None:
            return self._classify_with_model(texts)
        return [_keyword_classify(t) for t in texts]

    # ── Private ───────────────────────────────────────────────────────────────

    def _classify_with_model(self, texts: List[str]) -> List[Tuple[str, float]]:
        results: List[Tuple[str, float]] = []
        batch_size = config.SENTIMENT_BATCH_SIZE
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                outputs = self._pipe(batch)
                for output in outputs:
                    # pipeline returns list-of-list when top_k=1
                    item = output[0] if isinstance(output, list) else output
                    raw_label = item["label"].lower()
                    label = _LABEL_MAP.get(raw_label, "NEUTRAL")
                    score = float(item["score"])
                    results.append((label, score))
            except Exception as exc:  # noqa: BLE001
                logger.error("Model inference error: %s — using keyword fallback.", exc)
                results.extend([_keyword_classify(t) for t in batch])
        return results


# ── Keyword-based fallback classifier ────────────────────────────────────────
# Used when transformers is not available or model fails to load.

_NEGATIVE_PATTERNS = re.compile(
    r"\b(terrible|awful|horrible|bad|poor|sad|angry|outrage|furious|disgusting|"
    r"crime|gang|kidnap|violence|murder|shooting|corrupt|crisis|fail|dead|death|"
    r"fear|terror|protest|revolt|strike|suffering|starvation|poverty|disaster|"
    r"terrible|affreux|horrible|mauvais|triste|colère|corruption|crise|"
    r"criminalité|enlèvement|violence|meurtre|fusillade|peur|terreur|grève|"
    r"souffrance|famine|pauvreté|catastrophe|mouri|kriz|krim|gang|vyolans|"
    r"grangou|pòvrete|mouri|kidnaping|katastwòf|fè mal)\b",
    re.IGNORECASE,
)

_POSITIVE_PATTERNS = re.compile(
    r"\b(great|good|excellent|wonderful|amazing|happy|joy|love|peace|hope|"
    r"progress|success|victory|improve|better|grow|thrive|solidarity|"
    r"bien|excellent|merveilleux|magnifique|heureux|joie|paix|espoir|"
    r"progrès|succès|victoire|améliorer|solidarité|"
    r"bon|ekselan|bèl|kè kontan|lapè|espwa|pwogrè|siksè|viktwa|amelyore)\b",
    re.IGNORECASE,
)


def _keyword_classify(text: str) -> Tuple[str, float]:
    if not text:
        return ("NEUTRAL", 0.5)
    neg_hits = len(_NEGATIVE_PATTERNS.findall(text))
    pos_hits = len(_POSITIVE_PATTERNS.findall(text))
    if neg_hits > pos_hits:
        score = min(0.5 + neg_hits * 0.1, 0.95)
        return ("NEGATIVE", round(score, 3))
    if pos_hits > neg_hits:
        score = min(0.5 + pos_hits * 0.1, 0.95)
        return ("POSITIVE", round(score, 3))
    return ("NEUTRAL", 0.5)
