from __future__ import annotations

import logging
from collections import Counter
from typing import Dict, List, Optional, Tuple

from config import (
    NEGATIVE_KEYWORDS,
    POSITIVE_KEYWORDS,
    CATEGORY_KEYWORDS,
    CATEGORY_WEIGHTS,
    MAX_PER_ITEM_RISK,
    MAX_EFFECTIVE_ITEMS,
)
from models import NewsItemInput, NewsItemOutput, RiskSignalResponse


logger = logging.getLogger(__name__)


def _text_to_lower(text: Optional[str]) -> str:
    return (text or "").lower()


def detect_sentiment(text: str) -> str:
    lowered = text.lower()
    neg_hits = sum(1 for k in NEGATIVE_KEYWORDS if k in lowered)
    pos_hits = sum(1 for k in POSITIVE_KEYWORDS if k in lowered)

    if neg_hits > 0 and neg_hits >= pos_hits:
        return "negative"
    if pos_hits > 0 and pos_hits > neg_hits:
        return "positive"
    return "neutral"


def detect_categories(item: NewsItemInput) -> List[str]:
    text = " ".join(
        [
            _text_to_lower(item.headline),
            _text_to_lower(item.body),
            _text_to_lower(item.topic_hint),
        ]
    )
    categories: List[str] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            categories.append(category)

    if not categories:
        categories.append("other")

    return sorted(list(set(categories)))


def compute_item_risk(item: NewsItemInput) -> NewsItemOutput:
    text = " ".join(
        [
            _text_to_lower(item.headline),
            _text_to_lower(item.body),
        ]
    )

    sentiment = detect_sentiment(text)
    categories = detect_categories(item)

    affects_score = sentiment != "neutral"

    base_risk = 0.0
    if sentiment == "negative":
        base_risk = 5.0
    elif sentiment == "positive":
        base_risk = -2.0

    max_weight = max(CATEGORY_WEIGHTS.get(cat, 1.0) for cat in categories)
    risk_score = base_risk * max_weight

    if risk_score < 0:
        risk_contribution = int(max(-5.0, risk_score))
    else:
        risk_contribution = int(min(MAX_PER_ITEM_RISK, risk_score))

    if sentiment == "neutral":
        affects_score = False
        risk_contribution = 0

    return NewsItemOutput(
        headline=item.headline,
        sentiment=sentiment,  # type: ignore[arg-type]
        categories=categories,
        affects_score=affects_score,
        risk_contribution=risk_contribution,
    )


def aggregate_risk(
    item_outputs: List[NewsItemOutput],
) -> Tuple[int, str, List[str]]:
    total_raw = sum(o.risk_contribution for o in item_outputs if o.affects_score)

    max_theoretical = MAX_PER_ITEM_RISK * MAX_EFFECTIVE_ITEMS
    if max_theoretical <= 0:
        overall = 0
    else:
        normalized = (total_raw / max_theoretical) * 100.0
        overall = int(max(0, min(100, normalized)))

    if overall <= 33:
        level = "low"
    elif overall <= 66:
        level = "medium"
    else:
        level = "high"

    tag_counter: Counter[str] = Counter()
    for o in item_outputs:
        if o.affects_score:
            for c in o.categories:
                tag_counter[c] += 1

    top_tags = [tag for tag, _count in tag_counter.most_common(5)]
    if not top_tags:
        top_tags = ["other"]

    risk_tags = [f"{tag}_risk" for tag in top_tags]
    return overall, level, risk_tags


def build_summary_and_methodology(
    overall_risk_score: int,
    risk_level: str,
    top_risk_tags: List[str],
    items: List[NewsItemOutput],
) -> Dict[str, str]:
    dominant_tags = ", ".join(top_risk_tags[:3])

    if overall_risk_score >= 67:
        trend = "elevated and likely increasing"
    elif overall_risk_score >= 34:
        trend = "moderate and should be monitored"
    else:
        trend = "low and relatively stable"

    summary = (
        f"Current headline set indicates a {risk_level} risk environment "
        f"with dominant themes around {dominant_tags}. "
        f"Overall risk appears {trend} based on recent news. "
        f"Use this signal as a quick screening layer, not a full replacement for in-depth analysis."
    )

    methodology_note = (
        "This is a simple v1 heuristic based on keyword matching and category weights. "
        "Each negative headline increases the score depending on its category, while positive news can slightly offset risk. "
        "The overall score is normalized to a 0–100 range and mapped to low/medium/high bands. "
        "This is not a statistical or machine learning model and should be treated as an early signal only."
    )

    return {
        "summary": summary,
        "methodology_note": methodology_note,
    }


def compute_risk_signal(
    items: List[NewsItemInput], focus: Optional[str] = None, horizon_days: int = 7
) -> RiskSignalResponse:
    logger.info("Computing risk signal for %d items", len(items))

    item_outputs: List[NewsItemOutput] = [
        compute_item_risk(item) for item in items
    ]

    overall_risk_score, risk_level, top_risk_tags = aggregate_risk(item_outputs)

    meta = build_summary_and_methodology(
        overall_risk_score=overall_risk_score,
        risk_level=risk_level,
        top_risk_tags=top_risk_tags,
        items=item_outputs,
    )

    return RiskSignalResponse(
        overall_risk_score=overall_risk_score,
        risk_level=risk_level,  # type: ignore[arg-type]
        top_risk_tags=top_risk_tags,
        summary=meta["summary"],
        methodology_note=meta["methodology_note"],
        items=item_outputs,
    )
