from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


KnowledgeSourceType = Literal[
    "POLICY",
    "FAQ",
    "PRODUCT",
    "OPERATIONAL_NOTICE",
]


KnowledgeSourceStatus = Literal[
    "DRAFT",
    "PUBLISHED",
    "RETIRED",
]


class KnowledgeSectionInput(BaseModel):
    section: str = Field(
        min_length=1,
        max_length=500,
    )

    content: str = Field(
        min_length=1,
        max_length=100_000,
    )

    metadata: dict = Field(
        default_factory=dict,
    )


class KnowledgeSourceCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=500,
    )

    type: KnowledgeSourceType

    version: str = Field(
        min_length=1,
        max_length=100,
    )

    effective_at: datetime | None = None

    sections: list[
        KnowledgeSectionInput
    ] = Field(
        min_length=1,
    )

    metadata: dict = Field(
        default_factory=dict,
    )

    @field_validator(
        "effective_at",
    )
    @classmethod
    def validate_effective_at(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if (
            value is not None
            and value.tzinfo is None
        ):
            raise ValueError(
                "effective_at must include a timezone."
            )

        return value


class KnowledgeSourceUpdate(
    KnowledgeSourceCreate
):
    pass


class KnowledgeSection(BaseModel):
    id: UUID
    section: str | None
    content: str
    metadata: dict
    created_at: datetime


class KnowledgeSourceSummary(BaseModel):
    id: UUID

    title: str
    type: KnowledgeSourceType
    version: str
    status: KnowledgeSourceStatus

    effective_at: datetime | None
    last_updated: datetime

    checksum: str

    created_by: UUID | None
    created_at: datetime
    retired_at: datetime | None

    metadata: dict

    section_count: int


class KnowledgeSourceDetail(
    KnowledgeSourceSummary
):
    sections: list[
        KnowledgeSection
    ]


class KnowledgeSourceListResponse(
    BaseModel
):
    items: list[
        KnowledgeSourceSummary
    ]

    total: int


class KnowledgeRetireRequest(
    BaseModel
):
    reason: str = Field(
        min_length=3,
        max_length=1000,
    )