from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class KnowledgeIndexResponse(
    BaseModel
):
    source_id: UUID
    source_status: str

    provider: str
    model: str
    dimensions: int

    total_chunks: int
    embedded_chunks: int
    skipped_chunks: int

    prompt_tokens: int | None

    indexed_at: datetime