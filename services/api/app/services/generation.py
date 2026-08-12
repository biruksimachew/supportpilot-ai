import json

from dataclasses import dataclass
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

from app.schemas.grounded_generation import (
    GroundedModelOutput,
)


class GenerationConfigurationError(
    RuntimeError
):
    pass


class GenerationProviderError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class GenerationResult:
    output: GroundedModelOutput

    input_tokens: int | None
    output_tokens: int | None

    generation_ms: float | None


class GenerationProvider(Protocol):
    provider_name: str
    model: str

    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:
        ...


class OllamaGenerationProvider:
    provider_name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.base_url = (
            base_url.rstrip("/")
        )

        self.model = (
            model.strip()
        )

        self.timeout_seconds = (
            timeout_seconds
        )

        if not self.model:
            raise GenerationConfigurationError(
                "OLLAMA_MODEL is not configured."
            )


    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:

        schema = (
            GroundedModelOutput
            .model_json_schema()
        )


        request_body = json.dumps(
            {
                "model":
                    self.model,

                "messages": [
                    {
                        "role":
                            "system",

                        "content":
                            system_prompt,
                    },
                    {
                        "role":
                            "user",

                        "content":
                            user_prompt,
                    },
                ],

                "stream":
                    False,

                "think":
                    False,

                "format":
                    schema,

                "options": {
                    "temperature":
                        0.0,
                },
            }
        ).encode(
            "utf-8"
        )


        request = Request(
            (
                self.base_url
                + "/api/chat"
            ),

            method="POST",

            data=request_body,

            headers={
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
            raise GenerationProviderError(
                (
                    "Ollama generation request "
                    f"failed with HTTP {exc.code}."
                )
            ) from exc

        except (
            URLError,
            TimeoutError,
        ) as exc:
            raise GenerationProviderError(
                (
                    "Ollama generation service "
                    "is unavailable."
                )
            ) from exc

        except json.JSONDecodeError as exc:
            raise GenerationProviderError(
                (
                    "Ollama returned invalid JSON."
                )
            ) from exc


        message = (
            payload.get(
                "message"
            )
            or {}
        )

        content = (
            message.get(
                "content"
            )
        )


        if not isinstance(
            content,
            str,
        ):
            raise GenerationProviderError(
                (
                    "Ollama response did not "
                    "contain assistant content."
                )
            )


        try:
            structured = (
                GroundedModelOutput
                .model_validate_json(
                    content
                )
            )

        except Exception as exc:
            raise GenerationProviderError(
                (
                    "Ollama response violated "
                    "the grounded-output contract."
                )
            ) from exc


        total_duration = (
            payload.get(
                "total_duration"
            )
        )


        generation_ms = None

        if isinstance(
            total_duration,
            int,
        ):
            generation_ms = (
                total_duration
                / 1_000_000
            )


        return GenerationResult(
            output=
                structured,

            input_tokens=
                payload.get(
                    "prompt_eval_count"
                ),

            output_tokens=
                payload.get(
                    "eval_count"
                ),

            generation_ms=
                generation_ms,
        )


def get_generation_provider(
) -> GenerationProvider:

    provider_name = (
        settings
        .generation_provider
        .strip()
        .lower()
    )


    if provider_name == "ollama":
        return OllamaGenerationProvider(
            base_url=
                settings.ollama_base_url,

            model=
                settings.ollama_model,

            timeout_seconds=
                settings
                .generation_timeout_seconds,
        )


    raise GenerationConfigurationError(
        (
            "Unsupported generation provider: "
            f"{provider_name}"
        )
    )