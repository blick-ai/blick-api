"""
Schemas Pydantic de request/response para a API de usuários.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreateRequest(BaseModel):
    """Schema de requisição para criação de usuário."""

    full_name: str = Field(
        ..., min_length=2, max_length=255, examples=["João Silva"]
    )
    email: EmailStr = Field(
        ..., examples=["joao@fazenda.com"]
    )
    password: str = Field(
        ..., min_length=8, max_length=128
    )
    role: str = Field(
        default="producer",
        examples=["producer"],
        pattern="^(admin|technician|producer)$",
    )


class UserResponse(BaseModel):
    """Schema de resposta com dados do usuário."""

    id: uuid.UUID
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Schema de resposta para listagem paginada."""

    items: list[UserResponse]
    total: int
