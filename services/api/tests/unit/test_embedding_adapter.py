import math

import pytest

from app.services.embeddings import (
    EmbeddingProviderError,
    _expand_cosine_preserving,
)


def cosine(
    left: list[float],
    right: list[float],
) -> float:
    numerator = sum(
        a * b
        for a, b
        in zip(
            left,
            right,
            strict=True,
        )
    )

    left_norm = math.sqrt(
        sum(
            value * value
            for value in left
        )
    )

    right_norm = math.sqrt(
        sum(
            value * value
            for value in right
        )
    )

    return (
        numerator
        / (
            left_norm
            * right_norm
        )
    )


def test_dimension_expansion_preserves_cosine_similarity():
    left = [
        1.0,
        2.0,
        -1.0,
        0.5,
    ]

    right = [
        0.5,
        -1.0,
        3.0,
        2.0,
    ]

    native_similarity = cosine(
        left,
        right,
    )

    expanded_left = (
        _expand_cosine_preserving(
            left,
            16,
        )
    )

    expanded_right = (
        _expand_cosine_preserving(
            right,
            16,
        )
    )

    assert len(
        expanded_left
    ) == 16

    assert len(
        expanded_right
    ) == 16

    expanded_similarity = cosine(
        expanded_left,
        expanded_right,
    )

    assert expanded_similarity == pytest.approx(
        native_similarity,
        abs=1e-12,
    )


def test_dimension_expansion_requires_integer_multiple():
    with pytest.raises(
        EmbeddingProviderError
    ):
        _expand_cosine_preserving(
            [
                1.0,
                2.0,
                3.0,
            ],
            10,
        )