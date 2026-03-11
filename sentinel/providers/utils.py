import re


THINKING_PATTERNS = [
    re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<reasoning>.*?</reasoning>", re.DOTALL | re.IGNORECASE),
]


def strip_thinking_tags(text: str) -> str:
    cleaned = text
    for pattern in THINKING_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned.strip()
