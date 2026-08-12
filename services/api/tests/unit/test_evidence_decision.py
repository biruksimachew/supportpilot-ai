from datetime import (
    datetime,
    timezone,
)
from uuid import uuid4

from app.schemas.knowledge_retrieval import (
    KnowledgeRetrievalResponse,
    KnowledgeRetrievalResult,
)

from app.services.evidence_decision import (
    assess_evidence,
)


def make_result(
    *,
    similarity: float,
    source_id=None,
    source_metadata=None,
    chunk_metadata=None,
):
    return KnowledgeRetrievalResult(
        chunk_id=
            uuid4(),

        source_id=
            (
                source_id
                or uuid4()
            ),

        title=
            "Test Policy",

        type=
            "POLICY",

        version=
            "1.0",

        section=
            "Test",

        content=
            "Approved evidence.",

        similarity=
            similarity,

        effective_at=
            datetime(
                2026,
                8,
                1,
                tzinfo=timezone.utc,
            ),

        source_metadata=
            (
                source_metadata
                or {}
            ),

        chunk_metadata=
            (
                chunk_metadata
                or {}
            ),
    )


def make_retrieval(
    results,
):
    return KnowledgeRetrievalResponse(
        question=
            "Test question",

        provider=
            "test",

        model=
            "test-v1",

        dimensions=
            1536,

        top_k=
            5,

        min_similarity=
            0.0,

        results=
            results,
    )


def test_missing_evidence_fails_closed():
    assessment = (
        assess_evidence(
            make_retrieval(
                []
            )
        )
    )

    assert (
        assessment.confidence_band
        == "LOW"
    )

    assert (
        assessment.generation_allowed
        is False
    )

    assert (
        "EVIDENCE_MISSING"
        in assessment.reasons
    )


def test_high_evidence_allows_draft_generation():
    assessment = (
        assess_evidence(
            make_retrieval(
                [
                    make_result(
                        similarity=0.90
                    )
                ]
            )
        )
    )

    assert (
        assessment.confidence_band
        == "HIGH"
    )

    assert (
        assessment.generation_allowed
        is True
    )


def test_weak_evidence_blocks_generation():
    assessment = (
        assess_evidence(
            make_retrieval(
                [
                    make_result(
                        similarity=0.40
                    )
                ]
            )
        )
    )

    assert (
        assessment.confidence_band
        == "LOW"
    )

    assert (
        assessment.generation_allowed
        is False
    )


def test_explicit_policy_conflict_blocks_generation():
    first_source = (
        uuid4()
    )

    second_source = (
        uuid4()
    )


    assessment = (
        assess_evidence(
            make_retrieval(
                [
                    make_result(
                        similarity=0.90,

                        source_id=
                            first_source,

                        chunk_metadata={
                            "claim_key":
                                "return_window_days",

                            "claim_value":
                                30,
                        },
                    ),

                    make_result(
                        similarity=0.88,

                        source_id=
                            second_source,

                        chunk_metadata={
                            "claim_key":
                                "return_window_days",

                            "claim_value":
                                14,
                        },
                    ),
                ]
            )
        )
    )


    assert (
        assessment
        .contradiction_detected
        is True
    )

    assert (
        assessment
        .confidence_band
        == "LOW"
    )

    assert (
        assessment
        .generation_allowed
        is False
    )

    assert (
        "EVIDENCE_CONTRADICTORY"
        in assessment.reasons
    )
    from datetime import (
    datetime,
    timezone,
)
from uuid import uuid4

from app.schemas.knowledge_retrieval import (
    KnowledgeRetrievalResponse,
    KnowledgeRetrievalResult,
)

from app.services.evidence_decision import (
    assess_evidence,
)


def make_result(
    *,
    similarity: float,
    source_id=None,
    source_metadata=None,
    chunk_metadata=None,
):
    return KnowledgeRetrievalResult(
        chunk_id=
            uuid4(),

        source_id=
            (
                source_id
                or uuid4()
            ),

        title=
            "Test Policy",

        type=
            "POLICY",

        version=
            "1.0",

        section=
            "Test",

        content=
            "Approved evidence.",

        similarity=
            similarity,

        effective_at=
            datetime(
                2026,
                8,
                1,
                tzinfo=timezone.utc,
            ),

        source_metadata=
            (
                source_metadata
                or {}
            ),

        chunk_metadata=
            (
                chunk_metadata
                or {}
            ),
    )


def make_retrieval(
    results,
):
    return KnowledgeRetrievalResponse(
        question=
            "Test question",

        provider=
            "test",

        model=
            "test-v1",

        dimensions=
            1536,

        top_k=
            5,

        min_similarity=
            0.0,

        results=
            results,
    )


def test_missing_evidence_fails_closed():
    assessment = (
        assess_evidence(
            make_retrieval(
                []
            )
        )
    )

    assert (
        assessment.confidence_band
        == "LOW"
    )

    assert (
        assessment.generation_allowed
        is False
    )

    assert (
        "EVIDENCE_MISSING"
        in assessment.reasons
    )


def test_high_evidence_allows_draft_generation():
    assessment = (
        assess_evidence(
            make_retrieval(
                [
                    make_result(
                        similarity=0.90
                    )
                ]
            )
        )
    )

    assert (
        assessment.confidence_band
        == "HIGH"
    )

    assert (
        assessment.generation_allowed
        is True
    )


def test_weak_evidence_blocks_generation():
    assessment = (
        assess_evidence(
            make_retrieval(
                [
                    make_result(
                        similarity=0.40
                    )
                ]
            )
        )
    )

    assert (
        assessment.confidence_band
        == "LOW"
    )

    assert (
        assessment.generation_allowed
        is False
    )


def test_explicit_policy_conflict_blocks_generation():
    first_source = (
        uuid4()
    )

    second_source = (
        uuid4()
    )


    assessment = (
        assess_evidence(
            make_retrieval(
                [
                    make_result(
                        similarity=0.90,

                        source_id=
                            first_source,

                        chunk_metadata={
                            "claim_key":
                                "return_window_days",

                            "claim_value":
                                30,
                        },
                    ),

                    make_result(
                        similarity=0.88,

                        source_id=
                            second_source,

                        chunk_metadata={
                            "claim_key":
                                "return_window_days",

                            "claim_value":
                                14,
                        },
                    ),
                ]
            )
        )
    )


    assert (
        assessment
        .contradiction_detected
        is True
    )

    assert (
        assessment
        .confidence_band
        == "LOW"
    )

    assert (
        assessment
        .generation_allowed
        is False
    )

    assert (
        "EVIDENCE_CONTRADICTORY"
        in assessment.reasons
    )