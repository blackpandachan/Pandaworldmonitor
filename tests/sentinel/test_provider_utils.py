from sentinel.providers.utils import strip_thinking_tags


def test_strip_thinking_tags() -> None:
    text = "<think>analysis</think>final answer"
    assert strip_thinking_tags(text) == "final answer"
