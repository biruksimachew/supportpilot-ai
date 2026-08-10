import json
import math

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from urllib.error import (
    HTTPError,
    URLError,
)

from urllib.request import (
    Request,
    urlopen,
)

from app.core.config import settings


class EmbeddingConfigurationError(
    RuntimeError
):
    pass


class EmbeddingProviderError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[
        list[float]
    ]

    prompt_tokens: int | None


class EmbeddingProvider(Protocol):
    provider_name: str
    model: str
    dimensions: int

    def embed(
        self,
        texts: list[str],
    ) -> EmbeddingBatch:
        ...

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        ...


def _validate_vector(
    vector: list[float],
    *,
    dimensions: int,
) -> list[float]:
    if len(vector) != dimensions:
        raise EmbeddingProviderError(
            (
                "Embedding dimension mismatch: "
                f"expected {dimensions}, "
                f"received {len(vector)}."
            )
        )

    if not all(
        math.isfinite(value)
        for value in vector
    ):
        raise EmbeddingProviderError(
            "Embedding contains non-finite values."
        )

    return vector


def _expand_cosine_preserving(
    vector: list[float],
    target_dimensions: int,
) -> list[float]:
    native_dimensions = len(vector)

    if native_dimensions < 1:
        raise EmbeddingProviderError(
            "Embedding vector is empty."
        )

    if (
        target_dimensions
        % native_dimensions
        != 0
    ):
        raise EmbeddingProviderError(
            (
                "Target embedding dimension must "
                "be an integer multiple of the "
                "native model dimension."
            )
        )

    repeat_factor = (
        target_dimensions
        // native_dimensions
    )

    expanded = [
        float(value)
        for value in vector
        for _ in range(
            repeat_factor
        )
    ]

    norm = math.sqrt(
        sum(
            value * value
            for value in expanded
        )
    )

    if norm == 0:
        raise EmbeddingProviderError(
            "Embedding vector has zero magnitude."
        )

    normalized = [
        value / norm
        for value in expanded
    ]

    return _validate_vector(
        normalized,
        dimensions=target_dimensions,
    )


class FastEmbedLocalProvider:
    provider_name = "local-fastembed"

    def __init__(
        self,
        *,
        model: str,
        native_dimensions: int,
        dimensions: int,
        cache_dir: str,
    ) -> None:
        if dimensions < 1:
            raise EmbeddingConfigurationError(
                "Embedding dimensions must be positive."
            )

        if native_dimensions < 1:
            raise EmbeddingConfigurationError(
                (
                    "Local embedding native dimensions "
                    "must be positive."
                )
            )

        if (
            dimensions
            % native_dimensions
            != 0
        ):
            raise EmbeddingConfigurationError(
                (
                    "EMBEDDING_DIMENSIONS must be "
                    "an integer multiple of "
                    "LOCAL_EMBEDDING_NATIVE_DIMENSIONS."
                )
            )

        try:
            from fastembed import (
                TextEmbedding,
            )

        except ImportError as exc:
            raise EmbeddingConfigurationError(
                (
                    "FastEmbed is not installed. "
                    "Install the API dependencies."
                ) 
            ) from exc

        self.base_model = model

        self.native_dimensions = (
            native_dimensions
        )

        self.dimensions = dimensions

        repeat_factor = (
            dimensions
            // native_dimensions
        )

        self.model = (
            f"{model}"
            f"::repeat{repeat_factor}"
            f"-{dimensions}"
        )

        try:
            self._embedding_model = (
                TextEmbedding(
                    model_name=model,
                    cache_dir=cache_dir,
                )
            )

        except Exception as exc:
            raise EmbeddingProviderError(
                (
                    "The local embedding model "
                    "could not be loaded."
                )
            ) from exc


    def _prepare_vector(
        self,
        raw_vector,
    ) -> list[float]:
        vector = [
            float(value)
            for value
            in raw_vector
        ]

        if (
            len(vector)
            != self.native_dimensions
        ):
            raise EmbeddingProviderError(
                (
                    "Local embedding dimension "
                    "mismatch: expected "
                    f"{self.native_dimensions}, "
                    f"received {len(vector)}."
                )
            )

        return _expand_cosine_preserving(
            vector,
            self.dimensions,
        )


    def embed(
        self,
        texts: list[str],
    ) -> EmbeddingBatch:
        if not texts:
            return EmbeddingBatch(
                vectors=[],
                prompt_tokens=0,
            )

        if any(
            not text.strip()
            for text in texts
        ):
            raise EmbeddingProviderError(
                "Embedding input must not be empty."
            )

        try:
            raw_vectors = list(
                self._embedding_model
                .passage_embed(
                    texts
                )
            )

        except Exception as exc:
            raise EmbeddingProviderError(
                (
                    "Local embedding generation "
                    "failed."
                )
            ) from exc


        if (
            len(raw_vectors)
            != len(texts)
        ):
            raise EmbeddingProviderError(
                (
                    "Local provider returned an "
                    "unexpected vector count."
                )
            )


        vectors = [
            self._prepare_vector(
                raw_vector
            )
            for raw_vector
            in raw_vectors
        ]


        return EmbeddingBatch(
            vectors=vectors,
            prompt_tokens=None,
        )


    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        if not text.strip():
            raise EmbeddingProviderError(
                "Query embedding input must not be empty."
            )

        try:
            raw_vectors = list(
                self._embedding_model
                .query_embed(
                    text
                )
            )

        except Exception as exc:
            raise EmbeddingProviderError(
                (
                    "Local query embedding "
                    "generation failed."
                )
            ) from exc


        if len(raw_vectors) != 1:
            raise EmbeddingProviderError(
                (
                    "Local provider returned "
                    "an unexpected query vector count."
                )
            )


        return self._prepare_vector(
            raw_vectors[0]
        )


class OpenAIEmbeddingProvider:
    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimensions: int,
        timeout_seconds: int,
    ) -> None:
        if not api_key.strip():
            raise EmbeddingConfigurationError(
                "OPENAI_API_KEY is not configured."
            )

        if dimensions < 1:
            raise EmbeddingConfigurationError(
                "Embedding dimensions must be positive."
            )

        self.api_key = (
            api_key.strip()
        )

        self.model = model

        self.dimensions = (
            dimensions
        )

        self.timeout_seconds = (
            timeout_seconds
        )


    def embed(
        self,
        texts: list[str],
    ) -> EmbeddingBatch:
        if not texts:
            return EmbeddingBatch(
                vectors=[],
                prompt_tokens=0,
            )

        if any(
            not text.strip()
            for text in texts
        ):
            raise EmbeddingProviderError(
                "Embedding input must not be empty."
            )


        request_body = json.dumps(
            {
                "model":
                    self.model,

                "input":
                    texts,

                "dimensions":
                    self.dimensions,

                "encoding_format":
                    "float",
            }
        ).encode(
            "utf-8"
        )


        request = Request(
            (
                "https://api.openai.com"
                "/v1/embeddings"
            ),
            method="POST",
            data=request_body,
            headers={
                "Authorization":
                    (
                        "Bearer "
                        + self.api_key
                    ),

                "Content-Type":
                    "application/json",

                "Accept":
                    "application/json",
            },
        )


        try:
            with urlopen(
                request,
                timeout=
                    self.timeout_seconds,
            ) as response:
                payload = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

        except HTTPError as exc:
            error_code = None
            error_type = None

            try:
                error_payload = (
                    json.loads(
                        exc.read().decode(
                            "utf-8"
                        )
                    )
                )

                error = (
                    error_payload.get(
                        "error"
                    )
                    or {}
                )

                error_code = (
                    error.get(
                        "code"
                    )
                )

                error_type = (
                    error.get(
                        "type"
                    )
                )

            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
            ):
                pass


            details = [
                f"HTTP {exc.code}",
            ]

            if error_type:
                details.append(
                    f"type={error_type}"
                )

            if error_code:
                details.append(
                    f"code={error_code}"
                )


            raise EmbeddingProviderError(
                (
                    "OpenAI embedding request "
                    "failed: "
                    + ", ".join(
                        details
                    )
                    + "."
                )
            ) from exc

        except (
            URLError,
            TimeoutError,
        ) as exc:
            raise EmbeddingProviderError(
                (
                    "OpenAI embedding service "
                    "is unavailable."
                )
            ) from exc

        except json.JSONDecodeError as exc:
            raise EmbeddingProviderError(
                (
                    "OpenAI embedding response "
                    "was not valid JSON."
                )
            ) from exc


        raw_data = payload.get(
            "data"
        )

        if not isinstance(
            raw_data,
            list,
        ):
            raise EmbeddingProviderError(
                (
                    "OpenAI embedding response "
                    "did not contain data."
                )
            )


        ordered = sorted(
            raw_data,
            key=lambda item:
                item.get(
                    "index",
                    -1,
                ),
        )


        if len(ordered) != len(texts):
            raise EmbeddingProviderError(
                (
                    "OpenAI returned an unexpected "
                    "number of embeddings."
                )
            )


        vectors: list[
            list[float]
        ] = []


        for item in ordered:
            raw_vector = (
                item.get(
                    "embedding"
                )
            )

            if not isinstance(
                raw_vector,
                list,
            ):
                raise EmbeddingProviderError(
                    (
                        "OpenAI returned an "
                        "invalid embedding."
                    )
                )


            vector = [
                float(value)
                for value
                in raw_vector
            ]


            vectors.append(
                _validate_vector(
                    vector,
                    dimensions=
                        self.dimensions,
                )
            )


        usage = (
            payload.get(
                "usage"
            )
            or {}
        )

        prompt_tokens = (
            usage.get(
                "prompt_tokens"
            )
        )


        return EmbeddingBatch(
            vectors=vectors,

            prompt_tokens=(
                int(prompt_tokens)
                if prompt_tokens
                is not None
                else None
            ),
        )


    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        result = self.embed(
            [
                text,
            ]
        )

        if len(result.vectors) != 1:
            raise EmbeddingProviderError(
                (
                    "OpenAI returned an unexpected "
                    "query vector count."
                )
            )

        return result.vectors[0]


@lru_cache(
    maxsize=1,
)
def get_embedding_provider(
) -> EmbeddingProvider:
    provider_name = (
        settings
        .embedding_provider
        .strip()
        .lower()
    )


    if provider_name in (
        "local",
        "fastembed",
        "local-fastembed",
    ):
        return FastEmbedLocalProvider(
            model=
                settings
                .local_embedding_model,

            native_dimensions=
                settings
                .local_embedding_native_dimensions,

            dimensions=
                settings
                .embedding_dimensions,

            cache_dir=
                settings
                .local_embedding_cache_dir,
        )


    if provider_name == "openai":
        return OpenAIEmbeddingProvider(
            api_key=
                settings.openai_api_key,

            model=
                settings
                .openai_embedding_model,

            dimensions=
                settings
                .embedding_dimensions,

            timeout_seconds=
                settings
                .embedding_timeout_seconds,
        )


    raise EmbeddingConfigurationError(
        (
            "Unsupported embedding provider: "
            f"{provider_name}"
        )
    )