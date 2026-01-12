"""Application configuration from environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Google (Gemini)
    google_api_key: str = ""

    # Google Drive (credentials.json + token.pickle)
    google_drive_credentials_path: str = "credentials.json"
    google_drive_token_path: str = "token.pickle"

    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434"

    # Retry configuration
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0

    # Feature flags
    use_mock: bool = False  # Set to True to use mock implementations

    # Application
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
