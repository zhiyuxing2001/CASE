"""Application configuration, read from environment / ``.env``.

The API key lives here and never in the database. ``data/`` and ``.env``
are both gitignored, so patient material and secrets stay off the network
unless a request explicitly needs them.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings for the CASE backend."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- storage ---
    data_dir: Path = REPO_ROOT / "data"
    database_url: str = ""

    # --- DeepSeek ---
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_vision_model: str = "deepseek-flash"
    deepseek_text_model: str = "deepseek-flash"
    deepseek_reasoning_model: str = "deepseek-v4-pro"

    # --- server ---
    host: str = "127.0.0.1"
    port: int = 8765

    @property
    def db_path(self) -> Path:
        return self.data_dir / "case.db"

    @property
    def attachments_dir(self) -> Path:
        return self.data_dir / "attachments"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    def resolved_database_url(self) -> str:
        """Explicit ``DATABASE_URL`` wins; otherwise use ``data/case.db``."""
        return self.database_url or f"sqlite:///{self.db_path}"


settings = Settings()
