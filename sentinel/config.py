from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    sentinel_host: str = "0.0.0.0"
    sentinel_port: int = 8000
    sentinel_db_path: str = "./sentinel.db"
    sentinel_log_level: str = "INFO"
    sentinel_http_trust_env: bool = True

    gemini_api_key: str | None = None
    gemini_api_key_file: str | None = None
    gemini_volume_model: str = "gemini-3.1-flash-lite-preview"
    gemini_quality_model: str = "gemini-2.5-flash"

    ollama_api_url: str | None = None
    ollama_model: str = "llama3.1:8b"

    acled_api_key: str | None = None
    acled_api_key_file: str | None = None
    acled_email: str | None = None
    nasa_firms_api_key: str | None = None
    nasa_firms_api_key_file: str | None = None

    @staticmethod
    def _read_secret_file(path: str | None) -> str | None:
        if not path:
            return None
        candidate = Path(path)
        if not candidate.exists() or not candidate.is_file():
            return None
        value = candidate.read_text(encoding="utf-8").strip()
        return value or None

    @model_validator(mode="after")
    def load_secret_files(self) -> "Settings":
        self.gemini_api_key = self.gemini_api_key or self._read_secret_file(self.gemini_api_key_file)
        self.acled_api_key = self.acled_api_key or self._read_secret_file(self.acled_api_key_file)
        self.nasa_firms_api_key = self.nasa_firms_api_key or self._read_secret_file(self.nasa_firms_api_key_file)
        return self


settings = Settings()
