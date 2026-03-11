import json
import re
from functools import lru_cache
from pathlib import Path

from sentinel.models.news import Classification


@lru_cache
def _load_keywords() -> dict:
    path = Path(__file__).resolve().parent.parent / "data" / "keywords.json"
    return json.loads(path.read_text())


def classify_by_keyword(text: str) -> Classification:
    lowered = text.lower()
    config = _load_keywords()

    for phrase in config.get("exclude", []):
        if phrase in lowered:
            return Classification(severity="info", category="general", confidence=0.3, source="keyword")

    for rule in config.get("rules", []):
        keyword = rule["keyword"].lower()
        if len(keyword) <= 5:
            matched = bool(re.search(rf"\\b{re.escape(keyword)}\\b", lowered))
        else:
            matched = keyword in lowered
        if matched:
            return Classification(
                severity=rule["severity"],
                category=rule["category"],
                confidence=rule["confidence"],
                source="keyword",
            )

    return Classification(severity="info", category="general", confidence=0.3, source="keyword")
