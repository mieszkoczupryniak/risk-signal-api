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
    GRANULAR_RISK_TAG_RULES,  # NEW
)
from models import (
    NewsItemInput,
    NewsItemOutput,
    RiskSignalResponse,
    RiskSignalTrendRequest,   # NEW
    RiskSignalTrendResponse,  # NEW
    TrendPeriodSummary,       # NEW
    TrendDelta,               # NEW
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

# === Granular risk tags helper (NEW) ===

def derive_granular_tags_for_item(
    categories: List[str],
    region: Optional[str],
) -> List[str]:
    tags: set[str] = set()
    region_upper = (region or "").upper() or None

    for rule in GRANULAR_RISK_TAG_RULES:
        if rule["category"] not in categories:
            continue
        rule_region = rule["region"]
        # rule_region None => global tag for this category
        if rule_region is None or rule_region == region_upper:
            tags.add(rule["tag"])

    # fallback: jeśli nie złapaliśmy nic specyficznego, zrób ogólny tag
    if not tags:
        for cat in categories:
            tags.add(f"{cat}_risk")

    return list(tags)


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
) -> Tuple[int, str]:
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

    return overall, level


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

    # NEW: granular risk tags z kategorii + regionu
    granular_tags_counter: Counter[str] = Counter()
    for item, output in zip(items, item_outputs):
        if output.affects_score:
            item_tags = derive_granular_tags_for_item(
                categories=output.categories,
                region=item.region,
            )
            granular_tags_counter.update(item_tags)

    top_risk_tags = [tag for tag, _ in granular_tags_counter.most_common(5)]
    if not top_risk_tags:
        top_risk_tags = ["other_risk"]

    overall_risk_score, risk_level = aggregate_risk(item_outputs)

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

# === Trend computation (NEW) ===

def compute_trend(
    trend_request: RiskSignalTrendRequest,
) -> RiskSignalTrendResponse:
    baseline_req_items = trend_request.baseline.items
    current_req_items = trend_request.current.items

    baseline_result = compute_risk_signal(
        items=baseline_req_items,
        focus=trend_request.focus,
        horizon_days=trend_request.horizon_days,
    )
    current_result = compute_risk_signal(
        items=current_req_items,
        focus=trend_request.focus,
        horizon_days=trend_request.horizon_days,
    )

    score_change = (
        current_result.overall_risk_score - baseline_result.overall_risk_score
    )
    if score_change > 3:
        direction = "up"
    elif score_change < -3:
        direction = "down"
    else:
        direction = "flat"

    baseline_summary = TrendPeriodSummary(
        period_label=trend_request.baseline.period_label,
        overall_risk_score=baseline_result.overall_risk_score,
        risk_level=baseline_result.risk_level,
    )
    current_summary = TrendPeriodSummary(
        period_label=trend_request.current.period_label,
        overall_risk_score=current_result.overall_risk_score,
        risk_level=current_result.risk_level,
    )

    baseline_tags = Counter(baseline_result.top_risk_tags)
    current_tags = Counter(current_result.top_risk_tags)

    driver_scores: Counter[str] = Counter()
    for tag, count in current_tags.items():
        driver_scores[tag] += count
    for tag, count in baseline_tags.items():
        driver_scores[tag] -= count

    driver_tags = [
        tag for tag, score in driver_scores.most_common()
        if score > 0
    ][:5]
    if not driver_tags:
        driver_tags = current_result.top_risk_tags[:5]

    if direction == "up":
        comment = (
            f"Risk moved up by {score_change} points, "
            f"driven mainly by {', '.join(driver_tags[:3])}."
        )
    elif direction == "down":
        comment = (
            f"Risk moved down by {abs(score_change)} points, "
            f"partly offset by {', '.join(driver_tags[:3])}."
        )
    else:
        comment = (
            "Overall risk is broadly flat between periods with similar dominant tags."
        )

    delta = TrendDelta(
        score_change=score_change,
        direction=direction,
        comment=comment,
    )

    return RiskSignalTrendResponse(
        baseline=baseline_summary,
        current=current_summary,
        delta=delta,
        driver_tags=driver_tags,
        methodology_note=(
            "Trend is computed by running the existing heuristic on both periods "
            "and comparing scores."
        ),
    )

