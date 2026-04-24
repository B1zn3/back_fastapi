from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    LOGIN_RATE_LIMIT: int = 5   
    LOGIN_RATE_WINDOW: int = 300
    REFRESH_RATE_LIMIT: int = 10
    REFRESH_RATE_WINDOW: int = 300
    
    MAX_SESSIONS_PER_USER: int = 5
    ENVIRONMENT: str = "development"

    BACKEND_CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    )

    OTP_CODE_LENGTH: int = 6
    OTP_TTL_SECONDS: int = 600
    OTP_MAX_ATTEMPTS: int = 5
    PENDING_REGISTRATION_TTL_SECONDS: int = 1800

    EMAIL_ENABLED: bool = True
    EMAIL_FROM: str
    EMAIL_FROM_NAME: str = "JobFinder"

    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str

    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 20

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow"
    )

settings = Settings()