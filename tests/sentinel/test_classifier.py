from sentinel.analysis.classifier import classify_by_keyword


def test_conflict_keyword_classification() -> None:
    result = classify_by_keyword("Russia launches missile strike on Ukraine")
    assert result.severity == "high"
    assert result.category == "conflict"


def test_exclusion_prevents_false_positive() -> None:
    result = classify_by_keyword("New protein diet trending on TikTok")
    assert result.severity == "info"
    assert result.category == "general"
