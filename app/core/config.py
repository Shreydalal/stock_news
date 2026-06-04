import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Base App Configuration
    PROJECT_NAME: str = "Market Intelligence Bot"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./market_intelligence.db",
        description="Database connection string. Defaults to SQLite for local development."
    )

    # AI Integration
    GROQ_API: Optional[str] = Field(None, alias="GROQ_API")
    GROQ_API_KEY: Optional[str] = Field(None, alias="GROQ_API_KEY")

    # Data Sources
    ALPHA_VANTAGE_KEY: Optional[str] = None

    # Version Control / GitHub Automation
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPOSITORY: Optional[str] = Field(
        None, 
        description="GitHub repository in 'owner/repo' format. If empty, local git operations will run without pushing."
    )

    # Alerts & Notifications (Bonus Features)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Email SMTP configuration for Reports (Bonus Features)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_TO: Optional[str] = None

    @property
    def groq_key(self) -> Optional[str]:
        """Helper to get Groq API key whether set via GROQ_API or GROQ_API_KEY."""
        return self.GROQ_API_KEY or self.GROQ_API

settings = Settings()
