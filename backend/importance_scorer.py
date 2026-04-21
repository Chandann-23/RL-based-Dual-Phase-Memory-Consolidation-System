DATE_KEYWORDS = {
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "january", "february", "march", "april",
    "may", "june", "july", "august", "september", "october",
    "november", "december", "today", "tomorrow", "week", "month"
}


def compute_importance(unit: dict, max_freq: int) -> float:
    """
    Compute importance score ∈ [0, 1].

    importance =
      0.35 × normalized_frequency
    + 0.25 × recency_score
    + 0.20 × keyword_flag
    + 0.10 × contextual relevance
    + 0.10 × date relevance
    """
    freq_norm = unit["frequency"] / max(max_freq, 1)
    recency = unit.get("recency_score", 0.0)
    kw_flag = unit.get("keyword_flag", 0)
    contextual = 1.0 if unit["frequency"] > 1 else 0.0

    # Boost date-related concepts
    is_date = 1.0 if any(
        d in unit["concept"] for d in DATE_KEYWORDS
    ) else 0.0

    score = (
        0.35 * freq_norm
        + 0.25 * recency
        + 0.20 * kw_flag
        + 0.10 * contextual
        + 0.10 * is_date
    )
    return round(min(score, 1.0), 4)


def build_reasons(unit: dict, score: float, action: int) -> list[str]:
    """Human-readable reasons for the RL decision."""
    reasons = []
    if unit["frequency"] >= 3:
        reasons.append("High frequency of mention")
    elif unit["frequency"] >= 2:
        reasons.append("Mentioned more than once")
    if unit.get("recency_score", 0) >= 0.7:
        reasons.append("Recent mention in conversation")
    if unit.get("keyword_flag"):
        reasons.append("Importance keyword detected")
    if any(d in unit["concept"] for d in DATE_KEYWORDS):
        reasons.append("Date or time reference detected")
    if score >= 0.7:
        reasons.append("Overall high importance score")
    elif score >= 0.4:
        reasons.append("Moderate importance — kept in buffer")
    else:
        reasons.append("Low importance — candidate for removal")
    return reasons
