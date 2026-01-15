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

    # MCP Authentication
    mcp_bearer_token: str = ""  # Required for MCP API access

    # TOTP Authentication
    totp_secret: str = ""  # Base32 secret for TOTP (generate with pyotp.random_base32())
    totp_enabled: bool = True  # Enable/disable TOTP authentication
    totp_valid_window: int = 1  # Allow codes from ±1 time window (30 seconds each)
    session_secret: str = "change-me-in-production"  # Secret for signing session tokens

    # Application
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
