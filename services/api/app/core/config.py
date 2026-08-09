import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv(
        "APP_NAME",
        "SupportPilot AI",
    )

    environment: str = os.getenv(
        "APP_ENV",
        "local",
    )

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@host.docker.internal:55322/postgres",
    )

    chat_session_secret: str = os.getenv(
        "CHAT_SESSION_SECRET",
        "",
    )

    chat_session_ttl_minutes: int = int(
        os.getenv(
            "CHAT_SESSION_TTL_MINUTES",
            "480",
        )
    )


settings = Settings()