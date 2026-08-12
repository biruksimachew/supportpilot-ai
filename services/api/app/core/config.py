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
        (
            "postgresql://postgres:postgres"
            "@host.docker.internal:55322/postgres"
        ),
    )

    supabase_url: str = os.getenv(
        "SUPABASE_URL",
        "http://host.docker.internal:55321",
    )

    supabase_anon_key: str = os.getenv(
        "SUPABASE_ANON_KEY",
        "",
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

    web_origin: str = os.getenv(
        "WEB_ORIGIN",
        "http://127.0.0.1:3000",
    )

    email_ingest_secret: str = os.getenv(
        "EMAIL_INGEST_SECRET",
        "",
    )

    embedding_provider: str = os.getenv(
        "EMBEDDING_PROVIDER",
        "local",
    )

    embedding_dimensions: int = int(
        os.getenv(
            "EMBEDDING_DIMENSIONS",
            "1536",
        )
    )

    embedding_timeout_seconds: int = int(
        os.getenv(
            "EMBEDDING_TIMEOUT_SECONDS",
            "30",
        )
    )

    local_embedding_model: str = os.getenv(
        "LOCAL_EMBEDDING_MODEL",
        "BAAI/bge-small-en-v1.5",
    )

    local_embedding_native_dimensions: int = int(
        os.getenv(
            "LOCAL_EMBEDDING_NATIVE_DIMENSIONS",
            "384",
        )
    )

    local_embedding_cache_dir: str = os.getenv(
        "LOCAL_EMBEDDING_CACHE_DIR",
        "/var/cache/fastembed",
    )

    openai_embedding_model: str = os.getenv(
        "OPENAI_EMBEDDING_MODEL",
        "text-embedding-3-small",
    )

    openai_api_key: str = os.getenv(
        "OPENAI_API_KEY",
        "",
    )


    generation_provider: str = os.getenv(
        "GENERATION_PROVIDER",
        "ollama",
    )

    generation_timeout_seconds: int = int(
        os.getenv(
            "GENERATION_TIMEOUT_SECONDS",
            "180",
        )
    )

    ollama_base_url: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://ollama:11434",
    )

    ollama_model: str = os.getenv(
        "OLLAMA_MODEL",
        "qwen3:1.7b",
    )


settings = Settings()