import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class MeResponse(BaseModel):
    """Só identidade. Vínculos, personas e módulos habilitados vêm de `GET /api/me/contexto`
    e `GET /api/organizacoes/{orgId}/eu` (specs 04/05)."""

    id: uuid.UUID
    email: EmailStr
    name: str
