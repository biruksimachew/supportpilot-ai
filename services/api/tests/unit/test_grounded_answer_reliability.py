from uuid import uuid4

import pytest

from app.schemas.grounded_generation import (
    GroundedModelOutput,
)

from app.schemas.knowledge_retrieval import (
    KnowledgeRetrievalResponse,
    KnowledgeRetrievalResult,
)

from app.services.generation import (
    GenerationResult,
)

from app.services.grounded_answer import (
    GroundedGenerationConsistencyError,
    generate_grounded_answer,
)


def make_retrieval(
    *,
    with_result: bool = True,
) -> KnowledgeRetrievalResponse:

    results = []

    if with_result:

        results.append(
            KnowledgeRetrievalResult(
                chunk_id=
                    uuid4(),

                source_id=
                    uuid4(),

                title=
                    "Shipping Policy",

                type=
                    "POLICY",

                version=
                    "1.0",

                section=
                    "Standard Shipping",

                content=
                    (
                        "Standard shipping "
                        "takes 3 to 5 "
                        "business days."
                    ),

                similarity=
                    0.94,

                effective_at=
                    "2026-08-01T00:00:00Z",

                source_metadata={},
                chunk_metadata={},
            )
        )


    return KnowledgeRetrievalResponse(
        question=
            (
                "How long does "
                "standard shipping take?"
            ),

        provider=
            "test-embedding",

        model=
            "test-embedding-v1",

        dimensions=
            1536,

        top_k=
            5,

        min_similarity=
            0.0,

        results=
            results,
    )


class NeverCalledProvider:

    provider_name = "must-not-run"
    model = "must-not-run"

    calls = 0


    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ):

        self.calls += 1

        raise AssertionError(
            (
                "Generation must not run "
                "without evidence."
            )
        )


class RecoveringProvider:

    provider_name = "recovering-test"
    model = "recovering-test-v1"


    def __init__(
        self,
    ) -> None:

        self.calls = 0


    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:

        self.calls += 1

        if self.calls == 1:

            output = (
                GroundedModelOutput(
                    status=
                        "ANSWERED",

                    answer=
                        "Bad first attempt.",

                    citation_refs=[
                        "K999",
                    ],
                )
            )

        else:

            assert (
                "CORRECTION REQUIRED"
                in user_prompt
            )

            output = (
                GroundedModelOutput(
                    status=
                        "ANSWERED",

                    answer=
                        (
                            "Standard shipping "
                            "takes 3 to 5 "
                            "business days."
                        ),

                    citation_refs=[
                        "K1",
                    ],
                )
            )


        return GenerationResult(
            output=
                output,

            input_tokens=
                10,

            output_tokens=
                5,

            generation_ms=
                2.5,
        )


class PermanentlyInvalidProvider:

    provider_name = "invalid-test"
    model = "invalid-test-v1"


    def __init__(
        self,
    ) -> None:

        self.calls = 0


    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:

        self.calls += 1

        return GenerationResult(
            output=
                GroundedModelOutput(
                    status=
                        "ANSWERED",

                    answer=
                        "Still invalid.",

                    citation_refs=[
                        "K999",
                    ],
                ),

            input_tokens=
                1,

            output_tokens=
                1,

            generation_ms=
                1.0,
        )


def test_no_evidence_skips_generation():

    provider = (
        NeverCalledProvider()
    )


    result = (
        generate_grounded_answer(
            question=
                (
                    "How long does "
                    "standard shipping take?"
                ),

            retrieval=
                make_retrieval(
                    with_result=
                        False
                ),

            provider=
                provider,
        )
    )


    assert (
        result.status
        == "INSUFFICIENT_EVIDENCE"
    )

    assert result.citations == []

    assert provider.calls == 0


def test_invalid_first_attempt_can_recover():

    provider = (
        RecoveringProvider()
    )


    result = (
        generate_grounded_answer(
            question=
                (
                    "How long does "
                    "standard shipping take?"
                ),

            retrieval=
                make_retrieval(),

            provider=
                provider,
        )
    )


    assert provider.calls == 2

    assert result.status == "ANSWERED"

    assert (
        result.citations[0].ref
        == "K1"
    )

    assert result.input_tokens == 20

    assert result.output_tokens == 10

    assert result.generation_ms == 5.0


def test_repeated_invalid_grounding_fails_closed():

    provider = (
        PermanentlyInvalidProvider()
    )


    with pytest.raises(
        GroundedGenerationConsistencyError
    ):

        generate_grounded_answer(
            question=
                (
                    "How long does "
                    "standard shipping take?"
                ),

            retrieval=
                make_retrieval(),

            provider=
                provider,
        )


    assert provider.calls == 2
