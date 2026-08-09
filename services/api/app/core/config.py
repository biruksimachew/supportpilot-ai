import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "SupportPilot AI")
    environment: str = os.getenv("APP_ENV", "local")


settings = Settings()