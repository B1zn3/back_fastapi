from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---------- Database ----------
    DATABASE_URL: str

    # ---------- Redis ----------
    REDIS_URL: str

    # ---------- JWT ----------
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ---------- Rate limits ----------
    LOGIN_RATE_LIMIT: int = 5
    LOGIN_RATE_WINDOW: int = 300
    REFRESH_RATE_LIMIT: int = 10
    REFRESH_RATE_WINDOW: int = 300

    # ---------- Sessions ----------
    MAX_SESSIONS_PER_USER: int = 5

    # ---------- App ----------
    ENVIRONMENT: str = "development"

    BACKEND_CORS_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    # ---------- OTP ----------
    OTP_CODE_LENGTH: int = 6
    OTP_TTL_SECONDS: int = 600
    OTP_MAX_ATTEMPTS: int = 5
    PENDING_REGISTRATION_TTL_SECONDS: int = 1800

    # ---------- Email ----------
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

    # ---------- S3 / Timeweb Cloud ----------
    S3_ENDPOINT_URL: str
    S3_BUCKET: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_REGION: str = "ru-1"

    # Например:
    # https://s3.twcstorage.ru/bucket-name
    # или твой CDN/domain
    S3_PUBLIC_BASE_URL: str | None = None

    # Обычно можно оставить пустым.
    # Если Timeweb принимает public-read и бакет публичный:
    # S3_ACL=public-read
    S3_ACL: str | None = None

    # ---------- Upload limits ----------
    CHAT_MAX_FILE_SIZE_MB: int = 25
    PROFILE_IMAGE_MAX_SIZE_MB: int = 8
    MAX_CHAT_FILES_PER_MESSAGE: int = 10

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def s3_endpoint_url_normalized(self) -> str:
        return self.S3_ENDPOINT_URL.rstrip("/")

    @property
    def s3_public_base_url_normalized(self) -> str | None:
        if not self.S3_PUBLIC_BASE_URL:
            return None

        return self.S3_PUBLIC_BASE_URL.rstrip("/")

    @property
    def s3_acl_normalized(self) -> str | None:
        if not self.S3_ACL:
            return None

        acl = self.S3_ACL.strip()

        return acl or None

    @property
    def chat_max_file_size_bytes(self) -> int:
        return self.CHAT_MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def profile_image_max_size_bytes(self) -> int:
        return self.PROFILE_IMAGE_MAX_SIZE_MB * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )


settings = Settings()