import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "SupportPilot AI")
    environment: str = os.getenv("APP_ENV", "local")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@host.docker.internal:55322/postgres",
    )


settings = Settings()