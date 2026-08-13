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



    email_outbound_secret: str = os.getenv(
        "EMAIL_OUTBOUND_SECRET",
        "",
    )

    n8n_email_outbound_url: str = os.getenv(
        "N8N_EMAIL_OUTBOUND_URL",
        (
            "http://n8n:5678/webhook/"
            "supportpilot-email-outbound"
        ),
    )

    email_outbound_timeout_seconds: int = int(
        os.getenv(
            "EMAIL_OUTBOUND_TIMEOUT_SECONDS",
            "30",
        )
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


    evidence_high_similarity: float = float(
        os.getenv(
            "EVIDENCE_HIGH_SIMILARITY",
            "0.73",
        )
    )

    evidence_medium_similarity: float = float(
        os.getenv(
            "EVIDENCE_MEDIUM_SIMILARITY",
            "0.58",
        )
    )

    evidence_ambiguity_margin: float = float(
        os.getenv(
            "EVIDENCE_AMBIGUITY_MARGIN",
            "0.04",
        )
    )

    evidence_conflict_min_similarity: float = float(
        os.getenv(
            "EVIDENCE_CONFLICT_MIN_SIMILARITY",
            "0.58",
        )
    )

    commerce_provider: str = os.getenv(
        "COMMERCE_PROVIDER",
        "mock",
    )

    commerce_mock_base_url: str = os.getenv(
        "COMMERCE_MOCK_BASE_URL",
        "http://commerce-mock:8080",
    )

    commerce_timeout_seconds: int = int(
        os.getenv(
            "COMMERCE_TIMEOUT_SECONDS",
            "10",
        )
    )


settings = Settings()