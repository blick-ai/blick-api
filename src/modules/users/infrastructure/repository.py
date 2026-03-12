"""
Implementação concreta do repositório de usuários (Adapter).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.domain.entities import User
from src.modules.users.domain.repository import UserRepositoryPort
from src.modules.users.infrastructure.models import UserModel


class SqlAlchemyUserRepository(UserRepositoryPort):
    """Adapter que implementa UserRepositoryPort usando SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── Helpers de mapeamento ──────────────────────────

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            full_name=model.full_name,
            email=model.email,
            role=model.role,
            is_active=model.is_active,
            hashed_password=model.hashed_password,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_model(entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            full_name=entity.full_name,
            email=entity.email,
            role=entity.role,
            is_active=entity.is_active,
            hashed_password=entity.hashed_password,
        )

    # ── Implementação dos métodos do Port ──────────────

    async def get_by_id(
        self, entity_id: uuid.UUID
    ) -> User | None:
        result = await self._session.get(UserModel, entity_id)
        return self._to_entity(result) if result else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(
        self, skip: int = 0, limit: int = 100
    ) -> list[User]:
        stmt = select(UserModel).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [
            self._to_entity(m) for m in result.scalars().all()
        ]

    async def add(self, entity: User) -> User:
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update(self, entity: User) -> User:
        model = await self._session.get(UserModel, entity.id)
        if model:
            model.full_name = entity.full_name
            model.email = entity.email
            model.role = entity.role
            model.is_active = entity.is_active
            await self._session.flush()
            await self._session.refresh(model)
            return self._to_entity(model)
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        model = await self._session.get(UserModel, entity_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
