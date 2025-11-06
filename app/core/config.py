from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variables"""

    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # LiveKit Configuration
    LIVEKIT_API_KEY: str | None = None
    LIVEKIT_API_SECRET: str | None = None
    LIVEKIT_URL: str | None = None
    
    ASSEMBLYAI_API_KEY: str | None = None

    LOGFIRE_TOKEN: str | None = None
    
      # Database Configuration
    DATABASE_URL: str | None = None
    
     # Audio Configuration
    MAX_AUDIO_DURATION: int = 3600  # 1 hour max
    SUPPORTED_AUDIO_FORMATS: list = [".wav", ".mp3", ".m4a", ".webm"]
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    ENV: str = 'dev'

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()