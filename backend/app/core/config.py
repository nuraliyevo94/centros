from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "EduTrack AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # PostgreSQL Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres123"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "edutrack_db"
    DATABASE_URL: Optional[str] = None

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MQTT Settings
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_KEEPALIVE: int = 60

    # Security
    SECRET_KEY: str = "edutrack_super_secret_jwt_key_32_characters_long_min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Business Rules (Attendance Grace & Debt Limits)
    ATTENDANCE_GRACE_PERIOD_MINUTES: int = 10
    DOUBLE_TAP_PREVENTION_SECONDS: int = 300  # 5 minutes
    MAX_ALLOWED_DEBT_UZS: int = 200_000  # Soft block threshold

    # AI Pipeline Integrations
    GROQ_API_KEY: Optional[str] = None
    MOHIR_AI_API_KEY: Optional[str] = None
    MOHIR_AI_TTS_WS_URL: str = "wss://api.mohir.ai/v1/tts/stream"
    MOHIR_AI_STT_URL: str = "https://api.mohir.ai/v1/stt"

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_DIRECTOR_ALERTS_CHAT_ID: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
