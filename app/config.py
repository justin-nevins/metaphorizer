from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-4-20250514"
    database_url: str = "sqlite+aiosqlite:///./data/gatsby.db"
    gutenberg_url: str = "https://www.gutenberg.org/ebooks/64317.txt.utf-8"
    base_dir: Path = Path(__file__).resolve().parent.parent
    rate_limit_default: str = "30/minute"
    rate_limit_extraction: str = "5/minute"
    rate_limit_pdf: str = "10/minute"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
