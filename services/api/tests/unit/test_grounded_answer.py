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


class FakeGenerationProvider:
    provider_name = "test"
    model = "grounded-test-v1"

    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:

        assert (
            "ONLY the approved evidence"
            in system_prompt
        )

        assert (
            "30 calendar days"
            in user_prompt
        )

        return GenerationResult(
            output=
                GroundedModelOutput(
                    status=
                        "ANSWERED",

                    answer=(
                        "Yes. Unused items may "
                        "be returned within "
                        "30 calendar days."
                    ),

                    citation_refs=[
                        "K1",
                    ],
                ),

            input_tokens=100,
            output_tokens=25,
            generation_ms=50.0,
        )


class FakeBadCitationProvider:
    provider_name = "test"
    model = "bad-citation-test"

    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:

        return GenerationResult(
            output=
                GroundedModelOutput(
                    status=
                        "ANSWERED",

                    answer=
                        "Invented answer.",

                    citation_refs=[
                        "K999",
                    ],
                ),

            input_tokens=1,
            output_tokens=1,
            generation_ms=1.0,
        )


def make_retrieval(
) -> KnowledgeRetrievalResponse:

    return KnowledgeRetrievalResponse(
        question=
            "Can I return it?",

        provider=
            "test-embedding",

        model=
            "test-model",

        dimensions=
            1536,

        top_k=
            5,

        min_similarity=
            0.0,

        results=[
            KnowledgeRetrievalResult(
                chunk_id=
                    uuid4(),

                source_id=
                    uuid4(),

                title=
                    "Returns Policy",

                type=
                    "POLICY",

                version=
                    "1.0",

                section=
                    "Eligibility",

                content=(
                    "Unused items may be returned "
                    "within 30 calendar days."
                ),

                similarity=
                    0.92,

                effective_at=
                    "2026-08-01T00:00:00Z",

                source_metadata={},
                chunk_metadata={},
            )
        ],
    )


def test_grounded_answer_uses_supplied_evidence():
    result = generate_grounded_answer(
        question=
            "Can I return an unused item?",

        retrieval=
            make_retrieval(),

        provider=
            FakeGenerationProvider(),
    )

    assert result.status == "ANSWERED"

    assert (
        len(result.citations)
        == 1
    )

    assert (
        result.citations[0].ref
        == "K1"
    )

    assert (
        result.citations[0].title
        == "Returns Policy"
    )


def test_unknown_model_citation_is_rejected():
    with pytest.raises(
        GroundedGenerationConsistencyError
    ):
        generate_grounded_answer(
            question=
                "Can I return it?",

            retrieval=
                make_retrieval(),

            provider=
                FakeBadCitationProvider(),
        )