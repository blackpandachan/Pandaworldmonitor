from sentinel.config import Settings


def test_settings_reads_secret_file(tmp_path) -> None:
    key_file = tmp_path / "gemini.txt"
    key_file.write_text("test-secret\n", encoding="utf-8")

    settings = Settings(
        gemini_api_key=None,
        gemini_api_key_file=str(key_file),
    )

    assert settings.gemini_api_key == "test-secret"
