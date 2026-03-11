import os

import pytest

from sentinel.providers.router import LLMRouter


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not configured")
async def test_gemini_volume_tier_live_call() -> None:
    router = LLMRouter()
    result = await router.complete(
        tier="volume",
        messages=[{"role": "user", "content": "Return the single word: ready"}],
        timeout=20.0,
    )
    assert result is not None
    assert "ready" in result.content.lower()
