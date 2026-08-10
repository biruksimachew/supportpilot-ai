from typing import Literal
from uuid import UUID

from pydantic import BaseModel


StaffRole = Literal[
    "SUPPORT_AGENT",
    "SUPPORT_MANAGER",
    "SYSTEM_ADMIN",
]


class InternalUser(BaseModel):
    id: UUID
    email: str
    name: str
    role: StaffRole